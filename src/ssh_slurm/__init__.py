from .core.client import SlurmJob, SSHSlurmClient

__all__ = ["SSHSlurmClient", "SlurmJob"]


def hello() -> str:
    return "Hello from ssh-sbatch!"
