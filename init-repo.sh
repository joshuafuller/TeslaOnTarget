#!/bin/bash
# Initialize and push TeslaOnTarget to GitHub

echo "=== TeslaOnTarget GitHub Repository Setup ==="
echo
echo "Before running this script:"
echo "1. Create a new repo at https://github.com/new"
echo "   - Name: TeslaOnTarget"
echo "   - Public repository"
echo "   - DO NOT initialize with README, .gitignore, or license"
echo
read -p "Have you created the empty GitHub repository? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please create the repository first, then run this script again."
    exit 1
fi

echo "Initializing git repository..."
git init

echo "Adding all files..."
git add .

echo "Creating initial commit..."
git commit -m "Initial release of TeslaOnTarget v1.0.0

- Real-time Tesla vehicle tracking to TAK servers
- Docker support with easy authentication flow  
- Dead reckoning for smooth 1Hz updates
- Multi-vehicle support
- Comprehensive documentation
- GitHub Actions for automated Docker builds"

echo "Adding remote origin..."
git remote add origin https://github.com/joshuafuller/TeslaOnTarget.git

echo "Setting main branch..."
git branch -M main

echo "Pushing to GitHub..."
git push -u origin main

echo "Creating release tag..."
git tag -a v1.0.0 -m "Initial release - Tesla to TAK bridge"
git push origin v1.0.0

echo
echo "✅ Repository initialized and pushed!"
echo
echo "Next steps:"
echo "1. Check GitHub Actions at https://github.com/joshuafuller/TeslaOnTarget/actions"
echo "2. Docker images will be built automatically"
echo "3. Release will be created from the tag"
echo "4. Configure repository settings as needed"