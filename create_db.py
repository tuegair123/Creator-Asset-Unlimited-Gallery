import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# Inisialisasi koneksi DynamoDB ke LocalStack
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
    endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
)

def setup_database():
    print("Menghubungkan ke LocalStack...")
    try:
        # Membuat tabel baru bernama 'CreatorAssets'
        table = dynamodb.create_table(
            TableName='CreatorAssets',
            KeySchema=[
                # file_key akan menjadi Primary Key (sama seperti ID di MySQL)
                {'AttributeName': 'file_key', 'KeyType': 'HASH'} 
            ],
            AttributeDefinitions=[
                {'AttributeName': 'file_key', 'AttributeType': 'S'} # 'S' artinya String
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("Sedang membuat tabel 'CreatorAssets'... tunggu sebentar.")
        table.wait_until_exists()
        print("MANTAP! Tabel Database berhasil dibuat dan sudah aktif di LocalStack.")
        
    except Exception as e:
        # Jika tabel sudah ada, akan muncul peringatan ini
        print(f"Pesan Sistem: {str(e)}")

if __name__ == '__main__':
    setup_database()