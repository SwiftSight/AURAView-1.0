import boto3
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import mimetypes
from boto3.s3.transfer import TransferConfig
import uuid

# Initialize S3 client
s3_client = boto3.client('s3')

def upload_file(file_path, bucket_name, object_key):
    """
    Uploads a single file to S3.
    :param file_path: Local path to the file
    :param bucket_name: Target S3 bucket name
    :param object_key: Object key (file name in S3)
    :return: Tuple of (file_path, success, error_message)
    """
    try:
        # Detect content type
        content_type = mimetypes.guess_type(file_path)[0]
        extra_args = {'ContentType': content_type} if content_type else {}
        
        # Configure multipart upload
        config = TransferConfig(
            multipart_threshold=1024 * 25,  # 25MB
            max_concurrency=10,
            multipart_chunksize=1024 * 25,
            use_threads=True
        )
        
        s3_client.upload_file(
            file_path, 
            bucket_name, 
            object_key,
            ExtraArgs=extra_args,
            Config=config
        )
        return file_path, True, None
    except Exception as e:
        return file_path, False, str(e)

def upload_files_in_parallel(file_paths, bucket_name, folder_name, max_threads=4):
    """
    Uploads multiple files to S3 in parallel with progress tracking.
    :param folder_name: UUID-based folder name under which files will be uploaded
    :return: List of successful S3 paths
    """
    total_files = len(file_paths)
    completed = 0
    failed = []
    successful_paths = []  # New list to store successful S3 paths
    
    with ThreadPoolExecutor(max_threads) as executor:
        # Submit all upload tasks with folder path included
        future_to_file = {
            executor.submit(
                upload_file,
                file_path,
                bucket_name,
                f"{folder_name}/{os.path.basename(file_path)}"
            ): (file_path, f"{folder_name}/{os.path.basename(file_path)}") for file_path in file_paths
        }
        
        # Process completed uploads
        for future in as_completed(future_to_file):
            file_path, s3_path = future_to_file[future]
            file_path, success, error = future.result()
            completed += 1
            
            if success:
                print(f"[{completed}/{total_files}] Successfully uploaded: {file_path}")
                successful_paths.append(f"s3://{bucket_name}/{s3_path}")
            else:
                failed.append((file_path, error))
                print(f"[{completed}/{total_files}] Failed to upload {file_path}: {error}")
    
    # Report summary
    print(f"\nUpload Summary:")
    print(f"Successfully uploaded: {total_files - len(failed)}/{total_files} files")
    if failed:
        print("\nFailed uploads:")
        for file_path, error in failed:
            print(f"- {file_path}: {error}")

    return successful_paths

if __name__ == "__main__":
    try:
        # Configuration
        bucket_name = "your-s3-bucket-name"
        folder_name = str(uuid.uuid4())
        file_paths = [
            "/path/to/file1",
            "/path/to/file2",
            "/path/to/file3"
        ]
        max_threads = 8

        # Validate inputs
        if not bucket_name or bucket_name == "your-s3-bucket-name":
            raise ValueError("Please configure a valid bucket name")
        
        if not file_paths:
            raise ValueError("No files specified for upload")
            
        # Upload files and get S3 paths
        uploaded_paths = upload_files_in_parallel(file_paths, bucket_name, folder_name, max_threads)
        
        print(f"\nFiles uploaded to folder: {folder_name}")
        print("\nSuccessful S3 paths:")
        for path in uploaded_paths:
            print(f"- {path}")
        
    except Exception as e:
        print(f"Error: {e}")
