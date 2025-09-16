# Python Project Template

A template for Python projects with development container support and modern dependency management using `uv`.

## Getting Started

### 1. Create Your Project

Clone this template and initialize your new project:
```bash
# Clone the template
git clone https://github.com/skonop/setup my-project
cd my-project

# Initialize new git repository
make init-git
```

### 2. Check Development Environment

Verify your local environment has the required tools:
```bash
make check-env
```

This checks for:
- Python version
- `uv` package manager presence

### 3. Development Options

#### Option A: Using VS Code Dev Container (Recommended)
1. Install VS Code and the "Dev Containers" extension
2. Open the project folder in VS Code
3. When prompted, click "Reopen in Container" or run:
   - Command Palette (Cmd/Ctrl + Shift + P)
   - "Dev Containers: Rebuild and Reopen in Container"

The container will:
- Use Python 3.11
- Install `uv` package manager
- Install dependencies from `pyproject.toml`

#### Option B: Local Development
```bash
make local-dev
```

### 4. Project Configuration

1. Update `pyproject.toml`:
   - Set your project name, version, and description
   - Add your dependencies
   - Configure development tools

2. Update container settings (optional):
   - Edit `.devcontainer/devcontainer.json` for container customization
   - Add additional VS Code extensions or settings

### 5. Linking to Target Repo

1. Go to github, gitlab or other code versioning solution of your choice
2. Create a new repo, without adding any files to it (no README, license etc.)
3. Copy repo link and add it as remote to your local project
```bash
git remote add origin git@github.com:your_user/your_project.git
git branch -M main
git push -u origin main
```

## Project Structure

```
.
├── .devcontainer/          # Development container configuration
├── src/                    # Source code
│   ├── __init__.py
│   └── __main__.py        # Entry point
├── tests/                  # Test files
├── Makefile               # Development commands
└── pyproject.toml         # Project metadata and dependencies
```

## Available Make Commands

- `make help` - Show available commands
- `make init-git` - Initialize new git repository
- `make devcontainer` - Show instructions for dev container setup
- `make local-dev` - Run the project locally
- `make check-env` - Verify development environment

## Environment Variables

This template uses `prettyconf` for environment variable management. Create a `.env` file in your project root for local configuration.

## Testing the Template

Run the template tests to verify everything is working:
```bash
make test
```

This will:
1. Create a temporary test directory
2. Copy the template
3. Run through all main targets (`help`, `check-env`, `init-git`, `local-dev`)
4. Clean up the test directory

## Dev Container Troubleshooting

### Git push fails: "REMOTE HOST IDENTIFICATION HAS CHANGED!"
If you see:
```
WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
Host key verification failed.
```
Fix locally (inside the container):
```bash
ssh-keygen -R github.com
ssh-keyscan -H -t rsa,ecdsa,ed25519 github.com >> ~/.ssh/known_hosts
```
Notes:
- The dev container now refreshes GitHub host keys on creation to prevent this.
- This error can appear after GitHub rotates a host key or if an outdated key exists in `~/.ssh/known_hosts`.

### Using SSH keys inside the container

- Preferred: use your host SSH agent
  1. On the host, ensure a key is loaded:
     ```bash
     ssh-add -l || true
     # If empty, add one (example):
     ssh-add ~/.ssh/id_ed25519
     ```
  2. Inside the container, verify:
     ```bash
     ssh -T git@github.com
     ```
  Notes:
  - If `ssh-add -l` says “permission denied” inside the container, your host agent’s socket permissions don’t match the container user. The container will fall back to its own ssh-agent.

- Fallback: use a container-local ssh-agent
  ```bash
  # Generate a new key (no passphrase recommended only for throwaway dev)
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ''
  # Load it into the container ssh-agent
  ssh-add ~/.ssh/id_ed25519
  # Show the public key and add it to GitHub -> Settings -> SSH and GPG keys
  cat ~/.ssh/id_ed25519.pub
  # Test
  ssh -T git@github.com
  ```
