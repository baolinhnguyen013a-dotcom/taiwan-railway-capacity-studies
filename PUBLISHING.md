# Publish this folder to GitHub

These instructions publish only the `PUBLIC_UPLOAD` directory. Do not initialize or upload its parent `github_release_package` container, because that parent also contains the private `INTERNAL_DO_NOT_UPLOAD` archive.

## 1. Final local review

Open a terminal in the `PUBLIC_UPLOAD` directory, then run:

```bash
find . -name '.DS_Store' -o -name '__pycache__' -o -name '.pytest_cache'
```

The command should print nothing. Then create a virtual environment, install `requirements.txt`, and run the commands from the root README.

## 2. Create an empty GitHub repository

On GitHub, select **New repository** and choose a name such as `taiwan-railway-capacity-studies`. Do not ask GitHub to add a README, `.gitignore`, or license because this directory already contains them.

## 3. Initialize and inspect Git

```bash
git init
git branch -M main
git add .
git status --short
```

Review every staged path. There must be no political memo, `FINAL_SUBMISSION_REPORT_MOTC`, email draft, cache, local environment, compiler log, or internal audit report.

## 4. Commit and connect GitHub

Replace the example URL with your repository URL:

```bash
git commit -m "Initial public research release"
git remote add origin https://github.com/YOUR-ACCOUNT/taiwan-railway-capacity-studies.git
git push -u origin main
```

## 5. Verify after upload

1. Confirm the README warning and `LIMITATIONS.md` are visible.
2. Open **Actions** and confirm the workflow passes.
3. Run `git ls-files | rg 'DPP_TAICHUNG|FINAL_SUBMISSION_REPORT_MOTC|GEMINI_REVIEW|EMAIL_DRAFT'`; it should return no result.
4. Run `rg '/''Users/' .`; it should return no machine-specific absolute path.
5. Do not create a GitHub Release until author metadata and a deliberate licensing decision are available.
