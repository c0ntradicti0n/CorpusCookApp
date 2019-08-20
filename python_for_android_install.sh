rm ./buildozer.spec
pip install git+https://github.com/kivy/python-for-android.git
p4a --version
mkdir android
cd android
wget https://dl.google.com/android/repository/android-ndk-r17c-linux-x86_64.zip
unzip ./android-ndk-r17c-linux-x86_64.zip 
wget https://dl.google.com/android/repository/sdk-tools-linux-4333796.zip
unzip ./sdk-tools-linux-4333796.zip
cd ..
export ANDROIDSDK=$HOME/CorpusCookApp/android/
$ANDROIDSDK/tools/bin/sdkmanager "build-tools;27.0.3"
$ANDROIDSDK/tools/bin/sdkmanager "system-images;android-27;google_apis;x86"
$ANDROIDSDK/tools/bin/sdkmanager "platforms;android-27"
export ANDROIDNDK="$HOME/CorpusCookApp/android/android-ndk-r17c"
export ANDROIDAPI="27"  # Target API version of your application
export NDKAPI="27"  # Minimum supported API version of your application
export ANDROIDNDKVER="r17c"  # Version of the NDK you installed
pip install cython
p4a apk --private $HOME/CorpusCookApp/ --package=org.difference.app --name "Differencer" --version 0.1 --bootstrap=sdl2 --requirements=python3,kivy,regex,twisted,more_itertools,numpy

