import boto3
import json
import base64

# First lambda function handler: serialize data
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """A function to serialize target data from S3"""
    
    # Get the s3 address from the Step Function event input
    key = event["s3_key"]
    bucket = event["s3_bucket"]
    
    # Download the data from s3 to /tmp/image.png
    s3.download_file(bucket, key, "/tmp/image.png")
    
    # We read the data from a file
    with open("/tmp/image.png", "rb") as f:
        image_data = base64.b64encode(f.read())

    # Pass the data back to the Step Function
    print("Event:", event.keys())
    return {
        'statusCode': 200,
        'body': {
            "image_data": image_data,
            "s3_bucket": bucket,
            "s3_key": key,
            "inferences": []
        }
    }

# Second lambda function handler: classifying image
ENDPOINT = 'image-classification-2023-07-16-22-32-16-968'

def lambda_handler(event, context):
    # Decode the image data
    image = base64.b64decode(event["body"]["image_data"])
    
    # As discussed in a post on knowledge, we can use boto3 to get access to sagemaker
    # libraries instead of packaging the dependencies in a zip and uplodading it
    # to lambda
    # Get runtime
    runtime= boto3.client('runtime.sagemaker')
    # Get predictions
    response = runtime.invoke_endpoint(EndpointName=ENDPOINT,
                                           ContentType='image/png',Body=image)
    inferences = json.loads(response['Body'].read().decode('utf-8'))
    
    # We return the data back to the Step Function
    event["body"]["inferences"] = inferences
    return {
        'statusCode': 200,
        'body': json.dumps(event['body'])
    }

# Third lambda function handler: filter low confidence inferences
THRESHOLD = .80


def lambda_handler(event, context):
    body = json.loads(event["body"])
    # Grab the inferences from the event
    inferences = body["inferences"]
    
    # Check if any values in our inferences are above THRESHOLD
    meets_threshold = any(inference >= THRESHOLD for inference in inferences)
    
    # If our threshold is met, pass our data back out of the
    # Step Function, else, end the Step Function with an error
    if meets_threshold:
        pass
    else:
        raise("THRESHOLD_CONFIDENCE_NOT_MET")

    return {
        'statusCode': 200,
        'body': event['body']
    }
