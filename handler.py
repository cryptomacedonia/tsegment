import runpod, os, uuid, tempfile, subprocess, shutil, zipfile, boto3, requests

S3_BUCKET = os.getenv("OUTPUT_BUCKET")         # inject when you create the endpoint
s3 = boto3.client("s3",
                  endpoint_url=os.getenv("OUTPUT_ENDPOINT"),
                  aws_access_key_id=os.getenv("OUTPUT_KEY"),
                  aws_secret_access_key=os.getenv("OUTPUT_SECRET"))

def handler(event):
    """event["input"] must contain either:
         • url  – pre‑signed URL to a .zip or directory of DICOMs
         • nifti – base64‑encoded .nii.gz  (small cases only)
    returns: { "zipUrl": "https://…" }
    """
    jid   = event["id"] 
    work  = tempfile.mkdtemp(prefix=jid)       # /tmp is writeable in serverless
    inp   = os.path.join(work, "input.zip")
    out_d = os.path.join(work, "seg")

    # 1 · download & unzip
    with requests.get(event["input"]["url"], stream=True) as r:
        with open(inp, "wb") as f: shutil.copyfileobj(r.raw, f)
    subprocess.run(["unzip", "-q", inp, "-d", work], check=True)

    # 2 · (Option) convert DICOM→NIfTI
    if any(p.endswith(".dcm") for p in os.listdir(work)):
        import dicom2nifti, glob
        dicom2nifti.convert_directory(work, work, compression=True, reorient=True)

    img = [p for p in os.listdir(work) if p.endswith(".nii.gz")][0]

    # 3 · segment (≈ 90 s on an A10G)
    subprocess.run(["TotalSegmentator", "-i", img, "-o", out_d, "--fast"],
                   check=True)                 # “--fast” skips highest‑res pass  :contentReference[oaicite:1]{index=1}

    # 4 · package
    shutil.make_archive(out_d, "zip", out_d)   # → seg.zip

    # 5 · push to S3‑compatible store
    key = f"{jid}/seg.zip"
    s3.upload_file(f"{out_d}.zip", S3_BUCKET, key, ExtraArgs={"ACL": "public-read"})
    url = f"{os.getenv('OUTPUT_HTTP_PREFIX')}/{key}"

    shutil.rmtree(work)                        # clean temp
    return {"zipUrl": url}

runpod.serverless.start({"handler": handler})
