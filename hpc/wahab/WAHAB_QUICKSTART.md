# Wahab Quickstart

Local Windows upload:

```powershell
cd C:\Research\EpilepsyMortalityOptionB
.\hpc\wahab\local_pack_and_upload.ps1 -Midas pierpogb -HostName wahab.hpc.odu.edu
```

SSH and run:

```bash
ssh pierpogb@wahab.hpc.odu.edu
cd /home/pierpogb/EpilepsyMortalityOptionB
bash hpc/wahab/bootstrap_env.sh
bash hpc/wahab/stage_to_scratch.sh
bash hpc/wahab/submit_pipeline.sh
```

Monitor:

```bash
squeue -u pierpogb
bash hpc/wahab/monitor.sh
```

Fetch results on Windows:

```powershell
cd C:\Research\EpilepsyMortalityOptionB
.\hpc\wahab\local_fetch_results.ps1 -Midas pierpogb -HostName wahab.hpc.odu.edu
```

Open OnDemand alternative:

1. Log in to <https://ondemand.wahab.hpc.odu.edu/>.
2. Upload the project archive or open a shell.
3. Run the same Bash commands from `/home/pierpogb/EpilepsyMortalityOptionB`.
4. Monitor through Active Jobs or `bash hpc/wahab/monitor.sh`.
