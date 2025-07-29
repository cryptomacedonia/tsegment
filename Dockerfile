# syntax=docker/dockerfile:1
FROM --platform=linux/amd64 wasserth/totalsegmentator:2.10.0

# OS packages needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends unzip \
 && rm -rf /var/lib/apt/lists/*

# Python wheels for the RunPod worker
RUN pip install --no-cache-dir runpod==1.7.9 pydicom dicom2nifti boto3 requests

COPY handler.py /handler.py
ENTRYPOINT ["python", "-u", "/handler.py"]
