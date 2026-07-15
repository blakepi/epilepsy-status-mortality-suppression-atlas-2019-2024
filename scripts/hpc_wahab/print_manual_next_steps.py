from __future__ import annotations


def main() -> None:
    print("Windows upload:")
    print(r"cd C:\Research\EpilepsyMortalityOptionB")
    print(r".\hpc\wahab\local_pack_and_upload.ps1 -Midas pierpogb -HostName wahab.hpc.odu.edu")
    print("Wahab run:")
    print("ssh pierpogb@wahab.hpc.odu.edu")
    print("cd /home/pierpogb/EpilepsyMortalityOptionB")
    print("bash hpc/wahab/bootstrap_env.sh")
    print("bash hpc/wahab/stage_to_scratch.sh")
    print("bash hpc/wahab/submit_pipeline.sh")
    print("Monitor:")
    print("bash hpc/wahab/monitor.sh")
    print("Fetch:")
    print(r".\hpc\wahab\local_fetch_results.ps1 -Midas pierpogb -HostName wahab.hpc.odu.edu")


if __name__ == "__main__":
    main()
