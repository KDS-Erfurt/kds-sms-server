from sms_broker.settings import settings as _settings
_author_text = f"{_settings.branding.author} ({_settings.branding.author_email})"
ASCII_LOGO =f"""
[blue]╔══════════════════════════════════════════════════════╗[/blue]
[blue]║[/blue][white]  ____  __  __ ____    ____            _              [/white][blue]║[/blue]
[blue]║[/blue][white] / ___||  \/  / ___|  | __ ) _ __ ___ | | _____ _ __  [/white][blue]║[/blue]
[blue]║[/blue][white] \___ \| |\/| \___ \  |  _ \| '__/ _ \| |/ / _ \ '__| [/white][blue]║[/blue]
[blue]║[/blue][white]  ___) | |  | |___) | | |_) | | | (_) |   <  __/ |    [/white][blue]║[/blue]
[blue]║[/blue][white] |____/|_|  |_|____/  |____/|_|  \___/|_|\_\___|_|    [/white][blue]║[/blue]
[blue]╠══════════════════════════════════════════════════════╣[/blue]
[blue]║[/blue][white] {_settings.branding.description:53}[/white][blue]║[/blue]
[blue]║[/blue][white] by {_author_text:50}[/white][blue]║[/blue]
[blue]║[/blue][white] Version: [blue]v{_settings.branding.version:43}[/blue][/white][blue]║[/blue]
[blue]║[/blue][white] License: [green]{_settings.branding.license:44}[/green][/white][blue]║[/blue]
[blue]╚══════════════════════════════════════════════════════╝[/blue]"""

ASCII_LOGO = ASCII_LOGO[1:]
