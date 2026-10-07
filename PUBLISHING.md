# Publish to GitHub

The folder is already cleaned, initialized, and committed. If GitHub CLI is installed and logged in, publish it with these three lines:

```bash
cd /Users/saishangjiangnandong/Desktop/taiwan_railway_optimization/deliverables/github_release_package
git add . && git commit -m "Prepare public release" || true
gh repo create taiwan-railway-capacity-studies --public --source=. --remote=origin --push
```

Afterward, check the repository's **Actions** tab. The Taipei readiness audit intentionally remains limited to preliminary screening; this is documented in `LIMITATIONS.md`.
