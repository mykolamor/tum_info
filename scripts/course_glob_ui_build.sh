# Create a folder (named dmg) to prepare our DMG in (if it doesn't already exist).
mkdir -p dist/dmg
# Empty the dmg folder.
rm -r dist/dmg/*
# Copy the app bundle to the dmg folder.
cp -r "dist/Grades.app" dist/dmg
# If the DMG already exists, delete it.
test -f "dist/Grades.dmg" && rm "dist/Grades.dmg"
create-dmg \
  --volname "Grades" \
  --volicon "assets/icons/grade.icns" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --icon "Grades.app" 175 120 \
  --hide-extension "Grades.app" \
  --app-drop-link 425 120 \
  "dist/Grades.dmg" \
  "dist/dmg/"