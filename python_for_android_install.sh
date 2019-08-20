rm ./buildozer.spec
pip install git+https://github.com/kivy/python-for-android.git
p4a --version
mkdir android
cd android
wget https://dl.google.com/android/repository/android-ndk-r20-linux-x86_64.zip
unzip ./android-ndk-r17c-linux-x86_64.zip
wget https://dl.google.com/android/repository/sdk-tools-linux-4333796.zip
unzip ./sdk-tools-linux-4333796.zip
cd ..
export SDK_DIR=$HOME/PycharmProjects/CorpusCookApp/android/tools
$SDK_DIR/bin/sdkmanager "build-tools;26.0.2"
export ANDROIDNDK="$HOME/PycharmProjects/CorpusCookApp/android/android-ndk-r17c"
export ANDROIDAPI="26"  # Target API version of your application
export NDKAPI="26"  # Minimum supported API version of your application
export ANDROIDNDKVER="r17c"  # Version of the NDK you installed

p4a apk --private $HOME/PycharmProjects/CorpusCookApp/ --package=org.difference.app --name "Differencer" --version 0.1 --bootstrap=sdl2 --requirements=python3,kivy,regex,twisted,more_itertools,numpy

