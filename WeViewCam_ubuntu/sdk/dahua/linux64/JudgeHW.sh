#!/bin/bash
#确定当前程序的位数
is_64bit=`file './libplay.so'`
LibPath=""
if [[ $is_64bit =~ "64-bit" ]]
then
        is_64bit=1
        #使用find命令查找libc.so文件，每个电脑都会有lib.c
	libc_path=$(find /usr/lib -type f -name "libc.so" 2>/dev/null)
	
	# 判断是否找到了libc.so文件
	if [ -n "$libc_path" ]; then
    		# 提取不带libc.so的最终路径
    		LibPath=$(dirname "$libc_path")
	fi
	echo "is 64bit program"
else
        is_64bit=0
        #32位一般只有x86才会有版本路径使用i386
        LibPath="usr/lib/i386-linux-gnu"
        echo "is non 64bit program"
fi

#校验vdpau的软链接情况
VDPAU_info=`find $LibPath -maxdepth 1 -name 'libvdpau.so*' 2>&1`
if [[ $VDPAU_info =~ (libvdpau.so.1){1} ]]
then
	echo "VDPAU Driver is exist."
	vdpau_check=`find $LibPath -name 'libvdpau.so' 2>&1`
	if [[ $vdpau_check =~ (libvdpau.so){1} ]]
	then
		echo "libvdpau.so is exist in $vdpau_check"
	else
		echo "libvdpau.so is not exist, create a libvdpau.so in current path."
		vdpau_link=`find $LibPath -name 'libvdpau.so.1' 2>&1`
		ln -s $vdpau_link libvdpau.so
	fi
else
	echo "VDPAU Driver is not exist."
fi

#校验vaapi版本
va_version=2
va="libva.so.2"
vax11="libva-x11.so.2"
vaglx="libva-glx.so.2"
va_driver=`find $LibPath -maxdepth 1 -name 'libva*' 2>&1`
if [[ $va_driver =~ "libva.so.2" ]]
then
		va_version=2
		va="libva.so.2"
		vax11="libva-x11.so.2"
		vaglx="libva-glx.so.2"
		ln -s libHWDec.so.VA2 libHWDec.so
		echo "va2 found, create libHWDec.so->libHWDec.so.VA2!"
elif [[ $va_driver =~ "libva.so.1" ]]
then
		va_version=1
		va="libva.so.1"
		vax11="libva-x11.so.1"
		vaglx="libva-glx.so.1"
		ln -s libHWDec.so.VA1 libHWDec.so
		echo "va1 found, create libHWDec.so->libHWDec.so.VA1!"
else
		#如果不存在vaapi驱动，有可能只需要进行vdpau的硬解，libHWDec.so随便链接一个,且直接退出
		ln -s libHWDec.so.VA1 libHWDec.so
		echo "VA Driver is not exist,the vaapi could not run!link libHWDec.so->libHWDec.so.VA1"
		exit
fi

#校验vaapi的软链接情况
#libva.so
va_check=`find $LibPath -maxdepth 1 -name 'libva.so' 2>&1`
if [[ $va_check =~ "libva.so" ]]
then
	echo "libva.so is exist in $va_check"
else
	echo "libva.so is not exist, create a libva.so in current path."
	va_link=`find $LibPath -maxdepth 1 -name $va 2>&1`
	ln -s $va_link libva.so
fi
#libva-x11.so
vax11_check=`find $LibPath -maxdepth 1 -name 'libva-x11.so*' 2>&1`
if [[ $vax11_check =~ "libva-x11.so" ]] 
then
	echo "libva-x11.so* is exist."
	#find libva-x11.so
	vax11_check=`find $LibPath -maxdepth 1 -name 'libva-x11.so' 2>&1`
	if [[ $vax11_check =~ "libva-x11.so" ]]
	then
		echo "libva-x11.so is exist in $vax11_check"
	else
		echo "libva-x11.so is not exist, create a libva-x11.so in current path."
		vax11_link=`find $LibPath -maxdepth 1 -name $vax11 2>&1`
		ln -s $vax11_link libva-x11.so
	fi
else
	echo "libva-x11.so* is not exist,the vaapi could not run!"
fi
#libva-glx.so
vaglx_check=`find $LibPath -maxdepth 1 -name 'libva-glx.so*' 2>&1`
if [[ $vaglx_check =~ "libva-glx.so" ]]
then
	echo "libva-glx.so* is exist."
	#find libva-glx.so
	vaglx_check=`find $LibPath -maxdepth 1 -name 'libva-glx.so' 2>&1`
	if [[ $vaglx_check =~ "libva-glx.so" ]]
	then
		echo "libva-glx.so is exist in $vaglx_check"
	else
		echo "libva-glx.so is not exist, create a libva-glx.so in current path."
		vaglx_link=`find $LibPath -maxdepth 1 -name $vaglx 2>&1`
		ln -s $vaglx_link libva-glx.so
	fi
else
	echo "libva-glx.so* is not exist,the vaapi could not run!"
fi
