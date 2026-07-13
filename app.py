import os
from flask import Flask, render_template, request, redirect, url_for, flash
import boto3
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkeyuntukflashmessage"

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_DEFAULT_REGION'),
    endpoint_url=os.getenv('AWS_ENDPOINT_URL')
)

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
                
                cover_url = ""
                title = album_name
                description = "Belum ada deskripsi."
                raw_position = "50 50"
                
                # 1. Ambil Judul & Deskripsi dari Folder
                try:
                    tags = s3_client.get_object_tagging(Bucket=BUCKET_NAME, Key=folder_key)
                    for tag in tags.get('TagSet', []):
                        if tag['Key'] == 'Title': title = tag['Value']
                        if tag['Key'] == 'Description': description = tag['Value']
                except: pass
                
                # 2. Ambil Foto Terbaru sebagai Sampul
                contents_res = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=folder_key)
                if 'Contents' in contents_res:
                    # Dihapus reverse=True nya agar sampul selalu mengambil foto pertama (paling awal)
                    sorted_contents = sorted(contents_res['Contents'], key=lambda x: x['LastModified'])
                    for obj in sorted_contents:
                        if obj['Key'] != folder_key: # Abaikan file folder itu sendiri
                            cover_url = s3_client.generate_presigned_url('get_object', Params={'Bucket': BUCKET_NAME, 'Key': obj['Key']}, ExpiresIn=3600)
                            try:
                                img_tags = s3_client.get_object_tagging(Bucket=BUCKET_NAME, Key=obj['Key'])
                                for tag in img_tags.get('TagSet', []):
                                    if tag['Key'] == 'Position': raw_position = tag['Value']
                            except: pass
                            break # Cukup ambil 1 foto teratas
                
                pos_parts = raw_position.split()
                css_position = f"{pos_parts[0]}% {pos_parts[1]}%" if len(pos_parts) == 2 else "50% 50%"
                
                if cover_url: # Hanya tampilkan jika album ada isinya
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
        album_name = os.path.splitext(file.filename)[0] # Jadikan nama file sebagai nama album
        folder_key = f"{album_name}/"
        file_key = f"{album_name}/{file.filename}"
        
        try:
            s3_client.put_object(Bucket=BUCKET_NAME, Key=folder_key) # Buat Folder
            s3_client.upload_fileobj(file, BUCKET_NAME, file_key, ExtraArgs={"ContentType": file.content_type}) # Masukkan Foto
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
        s3_client.put_object_tagging(Bucket=BUCKET_NAME, Key=folder_key, Tagging={'TagSet': [{'Key': 'Title', 'Value': new_title}, {'Key': 'Description', 'Value': new_desc}]})
        
        contents = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=folder_key)
        if 'Contents' in contents:
            sorted_contents = sorted(contents['Contents'], key=lambda x: x['LastModified'], reverse=True)
            for obj in sorted_contents:
                if obj['Key'] != folder_key:
                    s3_client.put_object_tagging(Bucket=BUCKET_NAME, Key=obj['Key'], Tagging={'TagSet': [{'Key': 'Position', 'Value': new_pos}]})
                    break
        flash("Info album diperbarui!", "success")
    except Exception as e:
        flash(f"Gagal: {str(e)}", "danger")
        
    return redirect(url_for('dashboard'))

@app.route('/delete_album/<album_name>', methods=['POST'])
def delete_album(album_name):
    folder_key = f"{album_name}/"
    try:
        contents = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=folder_key)
        if 'Contents' in contents:
            for obj in contents['Contents']: s3_client.delete_object(Bucket=BUCKET_NAME, Key=obj['Key'])
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=folder_key)
        flash("Album berhasil dihapus!", "success")
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
    album_title = album_name # Default jika judul belum di-edit
    
    # --- TAMBAHAN BARU: Ambil judul dari Tag S3 Folder ---
    try:
        tags = s3_client.get_object_tagging(Bucket=BUCKET_NAME, Key=folder_key)
        for tag in tags.get('TagSet', []):
            if tag['Key'] == 'Title': album_title = tag['Value']
    except: pass
    # -----------------------------------------------------

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
        
    # Perhatikan: Sekarang kita mengirimkan album_title juga ke HTML
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