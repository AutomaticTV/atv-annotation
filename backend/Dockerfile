FROM nvidia/cuda:11.4.3-cudnn8-devel-ubuntu18.04

ENV PYTHONUNBUFFERED 1

ARG DEBIAN_FRONTEND=noninteractive

# Global dependences
RUN apt-get update
RUN apt-get install apt-utils -y
RUN apt-get install -y libsm6 libxext6 libxrender-dev ffmpeg make g++ qt5-default build-essential cmake git libgtk-3-dev
# Python
WORKDIR /app/
RUN apt-get install python3.8 python3-pip -y
COPY requirements.txt /app/
# Python script dependences
RUN pip3 install -r requirements.txt
RUN pip3 install patool
RUN pip3 install entrypoint2

RUN echo "/usr/local/cuda-11.4/compat" > /etc/ld.so.conf.d/libcuda.conf

RUN mkdir -p /app/codes
WORKDIR /app/codes/

# If darknet_cuda is set to 1 or darknet_opencv is set to 1, RUN apt-get install libopencv-dev -y
RUN echo "Building darknet with opencv"
RUN apt-get install libopencv-dev -y 
  
RUN echo "Darknet with cuda, and darknet with avx already in the source image"

#DARKNET
WORKDIR /app/library/
RUN git clone https://github.com/AlexeyAB/darknet.git
#COPY ./darknet /app/codes/darknet
WORKDIR /app/library/darknet
# Checkout commit 8a0bf84c19e38214219dbd3345f04ce778426c57
#RUN git checkout 8a0bf84c19e38214219dbd3345f04ce778426c57
#Set: GPU=1, CUDNN=1, CUDNN_HALF=1, OPENCV=1, OPENMP=1
RUN sed -i 's/GPU=0/GPU=1/g' Makefile
RUN sed -i 's/CUDNN=0/CUDNN=1/g' Makefile
RUN sed -i 's/CUDNN_HALF=0/CUDNN_HALF=1/g' Makefile
RUN sed -i 's/AVX=0/AVX=0/g' Makefile
RUN sed -i 's/OPENCV=0/OPENCV=1/g' Makefile
RUN sed -i 's/OPENMP=0/OPENMP=1/g' Makefile
RUN sed -i 's/LIBSO=0/LIBSO=1/g' Makefile
RUN make

RUN echo "2024-01-31 12:17"

WORKDIR /app/
COPY . /app/

CMD ["python3", "dashboard_app.py", "--log_level", "INFO"]
