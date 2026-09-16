import os
import shutil

LOCAL_CONFIG = r"D:\Loterias\LoteriasExtras\estrategias\lotteries_config.py"
DRIVE_DIR = r"I:\Meu Drive\CamposETC"
DRIVE_CONFIG = os.path.join(DRIVE_DIR, "lotteries_config.py")


def sync(verbose=False):
    """Backup opcional do lotteries_config no Google Drive. Não é usado na subida dos serviços."""
    if not os.path.exists(DRIVE_DIR):
        if verbose:
            print(f"Drive não acessível: {DRIVE_DIR}")
        return

    if not os.path.exists(DRIVE_CONFIG):
        shutil.copy2(LOCAL_CONFIG, DRIVE_CONFIG)
        if verbose:
            print("Backup inicial criado no Google Drive.")
        return

    mtime_local = os.path.getmtime(LOCAL_CONFIG)
    mtime_drive = os.path.getmtime(DRIVE_CONFIG)

    if mtime_local > mtime_drive + 2:
        shutil.copy2(LOCAL_CONFIG, DRIVE_CONFIG)
        if verbose:
            print("Drive atualizado.")
    elif mtime_drive > mtime_local + 2:
        shutil.copy2(DRIVE_CONFIG, LOCAL_CONFIG)
        if verbose:
            print("Arquivo local atualizado.")
    elif verbose:
        print("Já sincronizado.")


if __name__ == "__main__":
    sync(verbose=True)
