import tkinter as tk
import requests
import threading
import base64
import ctypes
from ctypes import wintypes
import json
import math
import os
from pathlib import Path
import queue
from urllib.parse import urlsplit
from tkinter import messagebox, ttk
from PIL import Image, ImageDraw, ImageFont
import pystray

currencies = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ETCUSDT', 'XRPUSDT', 'TRXUSDT', 'TONUSDT', 'SOLUSDT',
              'ETHBTC', 'BNBBTC', 'TONBTC', 'SOLBTC']
current_currency = currencies[0]
price_label = None
window_hidden = False
previous_price = None
stop_event = threading.Event()
condition = threading.Condition()
commands = queue.SimpleQueue()
results = queue.SimpleQueue()
generation = 0
connection_mode = 'system'
proxy_url = ''
proxy_window = None
timer = None
SETTINGS = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'BTCPriceOverlay' / 'settings.json'
ENDPOINT = 'https://api.binance.com/api/v3/ticker/price'

def get_price(currency, mode='system', proxy=''):
    try:
        if mode == 'custom':
            validate_proxy(proxy)
        with requests.Session() as session:
            session.trust_env = mode == 'system'
            if mode == 'custom':
                session.proxies = {'http': proxy, 'https': proxy}
            with session.get(ENDPOINT, params={'symbol': currency}, timeout=(3.05, 5)) as response:
                response.raise_for_status()
                data = response.json()
        price = float(data['price'])
        if data['symbol'] != currency or not math.isfinite(price) or price <= 0:
            raise ValueError('Invalid price response')
        return price
    except requests.exceptions.Timeout:
        return 'Connection timed out'
    except requests.exceptions.ProxyError:
        return 'Proxy unavailable'
    except requests.exceptions.HTTPError as error:
        return f'HTTP {error.response.status_code}'
    except requests.exceptions.RequestException:
        return 'Connection unavailable'
    except (ValueError, KeyError, TypeError):
        return 'Check connection settings'


def price_worker():
    # No Tkinter calls in this thread. Each response belongs to one selection.
    while not stop_event.is_set():
        with condition:
            selected = (generation, current_currency, connection_mode, proxy_url)
        result = get_price(*selected[1:])
        with condition:
            if stop_event.is_set():
                return
            if selected[0] != generation:
                continue
            results.put((selected[0], selected[1], result))
            condition.wait_for(lambda: stop_event.is_set() or generation != selected[0],
                               timeout=5 if isinstance(result, str) else 1)


def update_price():
    global previous_price, timer
    while not stop_event.is_set() and not commands.empty():
        callback, *args = commands.get()
        callback(*args)
    if stop_event.is_set():
        return
    while not results.empty():
        version, currency, price = results.get()
        if version != generation or currency != current_currency:
            continue
        if isinstance(price, str):
            price_label.config(text=price, fg='black')
        else:
            if previous_price is None:
                price_label.config(fg="black")
            elif price > previous_price:
                price_label.config(fg="green")
            elif price < previous_price:
                price_label.config(fg="red")
            else:
                price_label.config(fg="black")
            previous_price = price
            if price > 100:
                price = f"{price:,.2f}"
            elif price > 1:
                price = f"{price:,.3f}"
            elif price > 0.25:
                price = f"{price:,.4f}"
            else:
                price = str(price)
            if 'USD' in currency:
                price = '$' + price
            price_label.config(text=f"{currency}: {price}")
    timer = root.after(50, update_price)

def quit_app(*_):
    if stop_event.is_set():
        return
    with condition:
        stop_event.set()
        condition.notify_all()
    if timer is not None:
        root.after_cancel(timer)
    icon.stop()
    root.destroy()

def hide_window(*_):
    global window_hidden
    if window_hidden:
        root.deiconify()
        window_hidden = False
    else:
        root.withdraw()
        window_hidden = True
    update_tray_menu()

def set_currency(currency_key):
    global current_currency, previous_price, generation
    with condition:
        current_currency = str(currency_key)
        generation += 1
        condition.notify_all()
    previous_price = None
    price_label.config(text="Loading...", fg="black")
    update_tray_menu()

def create_image():
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), outline="black", fill="orange")
    try:
        font = ImageFont.truetype("arial", 36)
    except OSError:
        font = ImageFont.load_default(size=36)
    draw.text((18, 10), "B", font=font, fill="white")
    return image

def tray_action(callback, *args):
    def action(icon, item):
        commands.put((callback, *args))
    return action


def update_tray_menu():
    currency_menu = pystray.Menu(
        *[
            pystray.MenuItem(currency, tray_action(set_currency, currency),
                             checked=lambda item, cur=currency: current_currency == cur)
            for currency in currencies
        ]
    )
    
    menu = pystray.Menu(
        pystray.MenuItem('Currency', currency_menu),
        pystray.MenuItem('Connection / Proxy...', tray_action(show_proxy)),
        pystray.MenuItem('Show' if window_hidden else 'Hide', tray_action(hide_window)),
        pystray.MenuItem('Exit', tray_action(quit_app))
    )
    
    icon.menu = menu

def setup_tray():
    try:
        icon.run()
    except Exception:
        commands.put((tray_failed,))


def tray_failed():
    messagebox.showerror('BTC Price Overlay', 'Could not start the tray icon.', parent=root)
    quit_app()


def update_window_position(event=None):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = screen_width - window_width - 23
    y = 23
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

def validate_proxy(url):
    try:
        parts = urlsplit(url)
        valid = (parts.scheme in ('http', 'https', 'socks5', 'socks5h') and parts.hostname
                 and parts.port and parts.path in ('', '/') and not parts.query
                 and not parts.fragment and not any(c.isspace() for c in url))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Enter an HTTP, HTTPS, SOCKS5 or SOCKS5H URL with a host and port.')


def protect(data, decrypt=False):
    """Keep saved proxy credentials protected by the current Windows account."""
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_char))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    result = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    free = ctypes.WinDLL('kernel32').LocalFree
    free.argtypes, free.restype = [ctypes.c_void_p], ctypes.c_void_p
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        free(result.data)


def load_proxy():
    global connection_mode, proxy_url
    if not SETTINGS.exists():
        return
    try:
        data = json.loads(SETTINGS.read_text(encoding='utf-8'))
        connection_mode = data['mode']
        if connection_mode not in ('system', 'direct', 'custom'):
            raise ValueError('Invalid mode')
        if connection_mode == 'custom':
            proxy_url = protect(base64.b64decode(data['proxy'], validate=True), True).decode('utf-8')
            validate_proxy(proxy_url)
    except (OSError, ValueError, KeyError, TypeError):
        connection_mode, proxy_url = 'custom', ''
        commands.put((show_proxy,))


def show_proxy():
    global proxy_window
    if proxy_window is not None and proxy_window.winfo_exists():
        proxy_window.lift()
        return
    window = proxy_window = tk.Toplevel(root)
    window.title('Connection / Proxy')
    window.attributes('-topmost', True)
    window.resizable(False, False)
    body = ttk.Frame(window, padding=16)
    body.pack(fill='both', expand=True)
    mode = tk.StringVar(value=connection_mode)
    url = tk.StringVar(value=proxy_url)
    for value, label in [('system', 'System / environment proxy'), ('direct', 'Direct connection'),
                         ('custom', 'Custom proxy')]:
        ttk.Radiobutton(body, text=label, variable=mode, value=value).pack(anchor='w', pady=3)
    ttk.Label(body, text='Proxy URL').pack(anchor='w', pady=(10, 3))
    entry = ttk.Entry(body, textvariable=url, width=56, show='*')
    entry.pack(fill='x')
    show = tk.BooleanVar(value=False)
    ttk.Checkbutton(body, text='Show URL', variable=show,
                    command=lambda: entry.configure(show='' if show.get() else '*')).pack(anchor='w')
    ttk.Label(body, text='http://host:port or socks5h://host:port\n'
              'With login: http://username:password@host:port\n'
              'Saved credentials are protected by your Windows account.').pack(anchor='w', pady=8)

    def apply():
        global connection_mode, proxy_url, generation, previous_price
        new_mode = mode.get()
        new_proxy = url.get().strip() if new_mode == 'custom' else ''
        try:
            if new_mode == 'custom':
                validate_proxy(new_proxy)
            data = {'mode': new_mode}
            if new_proxy:
                data['proxy'] = base64.b64encode(protect(new_proxy.encode('utf-8'))).decode('ascii')
            SETTINGS.parent.mkdir(parents=True, exist_ok=True)
            temporary = SETTINGS.with_suffix('.tmp')
            temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
            temporary.replace(SETTINGS)
        except ValueError as error:
            messagebox.showerror('Proxy settings', str(error), parent=window)
            return
        except OSError:
            messagebox.showerror('Proxy settings', 'Could not save protected settings.', parent=window)
            return
        with condition:
            connection_mode, proxy_url = new_mode, new_proxy
            generation += 1
            condition.notify_all()
        previous_price = None
        price_label.config(text='Loading...', fg='black')
        window.destroy()

    ttk.Button(body, text='Save and reconnect', command=apply).pack(side='right')
    ttk.Button(body, text='Cancel', command=window.destroy).pack(side='right', padx=8)


def main():
    global root, icon, price_label, window_width, window_height, timer
    root = tk.Tk()
    root.title("Price Tracker")
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.7)
    root.overrideredirect(True)

    window_width = 180
    window_height = 26

    update_window_position()

    price_label = tk.Label(root, font=('Helvetica', 12))
    price_label.pack()

    root.bind('<Configure>', update_window_position)

    load_proxy()
    icon = pystray.Icon('price_tracker', create_image(), 'Price Tracker 0.2.0')
    update_tray_menu()
    root.protocol('WM_DELETE_WINDOW', quit_app)
    timer = root.after(0, update_price)

    threading.Thread(target=setup_tray, daemon=True).start()
    threading.Thread(target=price_worker, daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    main()
