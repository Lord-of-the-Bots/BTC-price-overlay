## BTC Price Overlay

BTC Price Overlay is an application that displays real-time cryptocurrency quotes based on Binance. The program runs in the background and displays the price of the selected cryptocurrency above all windows, including games, movies, and other applications running in borderless window mode. Management is done through an icon in the system tray.
- The compiled version for Windows x64 that does not require any installation to run (executable .exe) can be found in the Releases.

## Features

- Real-time display of the selected cryptocurrency price.
- Works above all windows.
- Convenient management through a system tray icon.
- Supports multiple cryptocurrencies from Binance.

## Requirements

- Windows and Python 3.10 or higher (Python 3.12 x64 is used for the release build)
- Libraries:
  - `tkinter`
  - `requests`
  - `threading`
  - `PIL` (Pillow)
  - `pystray`

## Installation

1. Clone the repository:
    git clone https://github.com/Lord-of-the-Bots/BTC-price-overlay.git
    cd btc-price-overlay

2. Install the necessary dependencies:
    pip install -r requirements.txt

## Usage

1. Run the script:
    python BTC_overlay.pyw

2. After launching the application, an icon will appear in the system tray. Right-click on it to configure and select the cryptocurrency to track.

You can also download and just run compiled Windows x64 release from releases page.

## Connection and proxy

Right-click the tray icon and open **Connection / Proxy...**:

- **System / environment proxy** uses the proxy settings detected by Python/Requests, including `HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY`. This is the default. Automatic PAC scripts are not supported.
- **Direct connection** ignores proxy settings.
- **Custom proxy** accepts `http://host:port`, `https://host:port`, `socks5://host:port` or `socks5h://host:port`. SOCKS5H resolves the destination hostname through the proxy.

For authentication, use `http://username:password@host:port` (or the corresponding SOCKS scheme). Percent-encode special characters in the username and password. Click **Save and reconnect** to apply the change without restarting. A failed custom proxy does not fall back to a direct connection.

Connection settings are saved in `%LOCALAPPDATA%\BTCPriceOverlay\settings.json`. Proxy URLs, including credentials, are encrypted using Windows DPAPI for the current Windows account. **Show URL** reveals the URL only in the settings window. Unreadable settings require selecting a connection mode again before networking resumes.

Price requests run in the background with connection/read timeouts. Changing the currency or proxy discards responses from the previous selection. **Exit** closes the window and tray without waiting for a pending price request.

## Build Windows EXE

From PowerShell with Python 3.12 x64 installed:

```powershell
.\build.ps1
```

The build creates `dist/BTC-price-overlay.exe` and `dist/SHA256SUMS.txt`. The EXE includes Python and its dependencies; no separate installation is needed to run it.

## Contributing

If you want to contribute to the project, please fork the repository, make your changes, and submit a pull request. We appreciate your contributions.

## License

This project is licensed under the MIT License. See the LICENSE.md file for details.

## Support development

If you value our projects, you can thank the developer with a cryptocurrency donation:

BTC (Bitcoin):
1NbtPNkofnKZRjLpULRjhKuAtbh12DovC9

USDT, TRX (TRC20):
TUgM6hPokF1vPUW8CRp77CgvF3YroabwFP

TON:
UQBLdOWJeVeVg4b0-HkQGNVV8HG6-xWS7moZOUfNBz2-Jf3u

ETH (ERC20):
0x14bba7b8b76ea4743a202bdee2144e4d558ddf93

LTC (Litecoin):
LRRS5YBeqfkYpw2jC2bDAWgpcgm7Wpu6pM
