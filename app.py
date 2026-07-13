import os
from flask import Flask, render_template, request, redirect, url_for, flash
import boto3
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkeyuntukflashmessage"

# 1. KONEKSI KE S3 LOCALSTACK
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
    endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
)

# 2. KONEKSI BARU KE DYNAMODB LOCALSTACK
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
    endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
)
db_table = dynamodb.Table('CreatorAssets')

BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

@app.route('/')
def welcome():
    return render_template('welcome.html')

# ==========================================
# HALAMAN 1: DASHBOARD (DAFTAR ALBUM)
# ==========================================
@app.route('/dashboard')
def dashboard():
    albums = []
    try:
        res = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Delimiter='/')
        if 'CommonPrefixes' in res:
            for prefix in res['CommonPrefixes']:
                folder_key = prefix['Prefix'] 
                album_name = folder_key.rstrip('/')
                
                # AMBIL METADATA DARI DATABASE DYNAMODB (Bukan S3 Tags lagi)
                db_item = {}
                try:
                    response = db_table.get_item(Key={'file_key': folder_key})
                    db_item = response.get('Item', {})
                except:
                    pass
                
                title = db_item.get('Title', album_name)
                description = db_item.get('Description', 'Belum ada deskripsi.')
                raw_position = db_item.get('Position', '50 50')
                
                # Ambil Foto Pertama sebagai Sampul dari S3
                cover_url = ""
                contents_res = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=folder_key)
                if 'Contents' in contents_res:
                    sorted_contents = sorted(contents_res['Contents'], key=lambda x: x['LastModified'])
                    for obj in sorted_contents:
                        if obj['Key'] != folder_key:
                            cover_url = s3_client.generate_presigned_url('get_object', Params={'Bucket': BUCKET_NAME, 'Key': obj['Key']}, ExpiresIn=3600)
                            break 
                
                pos_parts = raw_position.split()
                css_position = f"{pos_parts[0]}% {pos_parts[1]}%" if len(pos_parts) == 2 else "50% 50%"
                
                if cover_url: 
                    albums.append({
                        'name': album_name,
                        'title': title,
                        'description': description,
                        'cover_url': cover_url,
                        'position': css_position
                    })
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        
    return render_template('index.html', albums=albums)

@app.route('/upload_album', methods=['POST'])
def upload_album():
    if 'file' not in request.files: return redirect(url_for('dashboard'))
    file = request.files['file']
    
    if file.filename != '':
        album_name = os.path.splitext(file.filename)[0]
        folder_key = f"{album_name}/"
        file_key = f"{album_name}/{file.filename}"
        
        try:
            s3_client.put_object(Bucket=BUCKET_NAME, Key=folder_key) 
            s3_client.upload_fileobj(file, BUCKET_NAME, file_key, ExtraArgs={"ContentType": file.content_type}) 
            
            # INISIALISASI DATA AWAL KE DATABASE
            db_table.put_item(
                Item={
                    'file_key': folder_key,
                    'Title': album_name,
                    'Description': 'Belum ada deskripsi.',
                    'Position': '50 50'
                }
            )
            flash(f"Album baru dibuat!", "success")
        except Exception as e:
            flash(f"Gagal membuat album: {str(e)}", "danger")
            
    return redirect(url_for('dashboard'))

@app.route('/update_album/<album_name>', methods=['POST'])
def update_album(album_name):
    new_title = request.form.get('title')
    new_desc = request.form.get('description')
    new_pos = request.form.get('position').replace('%', '')
    folder_key = f"{album_name}/"
    
    try:
        # UPDATE DATA LANGSUNG KE DATABASE
        db_table.put_item(
            Item={
                'file_key': folder_key,
                'Title': new_title,
                'Description': new_desc,
                'Position': new_pos
            }
        )
        flash("Info album diperbarui via Database!", "success")
    except Exception as e:
        flash(f"Gagal: {str(e)}", "danger")
        
    return redirect(url_for('dashboard'))

@app.route('/delete_album/<album_name>', methods=['POST'])
def delete_album(album_name):
    folder_key = f"{album_name}/"
    try:
        # 1. Hapus isi S3
        contents = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=folder_key)
        if 'Contents' in contents:
            for obj in contents['Contents']: s3_client.delete_object(Bucket=BUCKET_NAME, Key=obj['Key'])
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=folder_key)
        
        # 2. Hapus catatan dari Database
        db_table.delete_item(Key={'file_key': folder_key})
        
        flash("Album dan Data berhasil dihapus!", "success")
    except Exception as e:
        flash(f"Gagal menghapus: {str(e)}", "danger")
    return redirect(url_for('dashboard'))

# ==========================================
# HALAMAN 2: ISI ALBUM FOTO
# ==========================================
@app.route('/album/<album_name>')
def view_album(album_name):
    photos = []
    folder_key = f"{album_name}/"
    
    # AMBIL JUDUL ALBUM DARI DATABASE
    album_title = album_name 
    try:
        response = db_table.get_item(Key={'file_key': folder_key})
        if 'Item' in response:
            album_title = response['Item'].get('Title', album_name)
    except:
        pass

    try:
        res = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=folder_key)
        if 'Contents' in res:
            sorted_contents = sorted(res['Contents'], key=lambda x: x['LastModified'], reverse=True)
            for obj in sorted_contents:
                if obj['Key'] != folder_key:
                    url = s3_client.generate_presigned_url('get_object', Params={'Bucket': BUCKET_NAME, 'Key': obj['Key']}, ExpiresIn=3600)
                    display_name = obj['Key'].replace(folder_key, '')
                    photos.append({'key': obj['Key'], 'name': display_name, 'url': url})
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        
    return render_template('album.html', photos=photos, album_name=album_name, album_title=album_title)

@app.route('/upload_photo/<album_name>', methods=['POST'])
def upload_photo(album_name):
    if 'file' not in request.files: return redirect(url_for('view_album', album_name=album_name))
    file = request.files['file']
    if file.filename != '':
        file_key = f"{album_name}/{file.filename}"
        try:
            s3_client.upload_fileobj(file, BUCKET_NAME, file_key, ExtraArgs={"ContentType": file.content_type})
            flash("Foto berhasil ditambahkan ke album!", "success")
        except Exception as e:
            flash(f"Gagal upload: {str(e)}", "danger")
    return redirect(url_for('view_album', album_name=album_name))

@app.route('/delete_photo/<path:key>', methods=['POST'])
def delete_photo(key):
    album_name = key.split('/')[0]
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=key)
        flash("Foto dihapus!", "success")
    except Exception as e:
        flash(f"Gagal menghapus: {str(e)}", "danger")
    return redirect(url_for('view_album', album_name=album_name))

if __name__ == '__main__':
    app.run(debug=True)