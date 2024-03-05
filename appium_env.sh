#!/bin/zsh
# 檢查 Android SDK 路徑並寫入 ~/.zshrc
if [ -d "$HOME/Library/Android/sdk" ]; then
	echo '# ANDROID ENV'  >> ~/.zshrc
    echo 'export ANDROID_HOME="$HOME/Library/Android/sdk"' >> ~/.zshrc
else
    echo "Android SDK 路徑不存在"
fi
echo 'export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"' >> ~/.zshrc
echo '# JAVA ENV'  >> ~/.zshrc
# 將 JAVA_HOME 設定寫入 ~/.zshrc
echo 'export JAVA_HOME=$(/usr/libexec/java_home)' >> ~/.zshrc
# 將 PATH 和 CLASS_PATH 設定寫入 ~/.zshrc
echo 'export CLASS_PATH="$JAVA_HOME/lib"' >> ~/.zshrc
# 重新加載 .zshrc 檔案
source $HOME/.zshrc
echo ".zshrc 檔案已更新"
