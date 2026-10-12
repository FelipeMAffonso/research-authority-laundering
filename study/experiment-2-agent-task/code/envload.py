"""Load vendor keys from the Windows user environment when the current shell did not inherit them.

Vendor keys are user-scope environment variables; they are read from the environment and never written
into a file. A shell started before a key was set does not see it, so fall back to the registry (HKCU).
"""
import os

KEY_NAMES = ("OPENAI_API_KEY", "OPENROUTER_API_KEY")


def load_user_env(names=KEY_NAMES) -> dict:
    """Fill os.environ for any missing name from HKCU\\Environment. Returns {name: 'env'|'registry'|'missing'}."""
    status = {}
    missing = []
    for n in names:
        if os.environ.get(n):
            status[n] = "env"
        else:
            missing.append(n)
    if missing:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                for n in missing:
                    try:
                        v, _ = winreg.QueryValueEx(k, n)
                    except FileNotFoundError:
                        v = ""
                    if v:
                        os.environ[n] = v
                        status[n] = "registry"
                    else:
                        status[n] = "missing"
        except ImportError:
            for n in missing:
                status[n] = "missing"
    return status


if __name__ == "__main__":
    print(load_user_env())
