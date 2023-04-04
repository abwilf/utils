# pip install google-api-python-client gdown google_auth_oauthlib
from __future__ import print_function
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from apiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
import gdown
import sys; sys.path.append('/work/awilf/utils/'); from alex_utils import *
import traceback
IMMORTAL_FOLDER_ID = '1zBldu3ipR6LtrJBxxNlaKBPW_kio6nli'


def get_service(credentials_path, token_path, scopes=['https://www.googleapis.com/auth/drive']):
    # If need to regen token: 
    # ssh -N -f -L localhost:8080:localhost:8080 awilf@taro
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            creds = flow.run_local_server(port=8080)

        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)
    return service

def gdrive_up(file_list, folder_id, credentials_path, token_path='/work/awilf/utils/gdrive_token.json', rm_after=False):
    '''
    file_list: full path of files to upload, e.g. ['/work/awilf/tonicnet.tar'] or folder (in which case upload all)
    folder_id: id of folder you've already created in google drive (awilf@andrew account, for these credentials)
    credentials_path: json containing gdrive credentials of form {"installed":{"client_id":"<something>.apps.googleusercontent.com","project_id":"decisive-engine-<something>","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"<client_secret>","redirect_uris":["urn:ietf:wg:oauth:2.0:oob","http://localhost"]}}

    e.g. 
    gdrive_up('gdrive_credentials.json', ['hi.txt', 'yo.txt'], '1E1ub35TDJP59rlIqDBI9SLEncCEaI4aT')

    note: if token_path does not exist, you will need to authenticate. here are the instructions

    ON MAC: ssh -N -f -L localhost:8080:localhost:8080 awilf@taro
    ON MAC (CHROME): go to link provided
    '''

    service = get_service(credentials_path, token_path)

    if isdir(file_list[0]):
        file_list = glob(join(file_list[0],'*'))
        
    ret_obs = []
    for name in tqdm(file_list):
        if not exists(name):
            print(f'FILENAME {name} does not exist...moving on')
            continue
        file_metadata = {
            'name': rsp(name),
            'parents': [folder_id]
        }
        try:
            media = MediaFileUpload(name, resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            
            if rm_after:
                rm(name)
            ret_obs.append(file)

        except Exception as e:
            print(f'ALERT: FILE {name} was not uploaded because of an error {traceback.format_exc()}')
            exit()
    return ret_obs
    
def download_file(file_id, file_path, service, num_tries=3):
    '''
    if . in file_path, treat it as a whole filename
    else get the name from the request object and fill that in
    '''
    request = service.files().get_media(fileId=file_id)
    if '.' not in rsp(file_path):
        assert exists(file_path) and isdir(file_path), 'If you are downloading a file, the dl_path provided must be an existing directory or have an extension with a "." (e.g. hi.txt)'
        file = service.files().get(fileId=file_id).execute()
        file_path = join(file_path, file['name']) # when you just pass in a directory to download a file

    this_try = 0
    while this_try < num_tries:
        try:
            if exists(file_path) and gc['skip_existing']:
                print(f'Skipping {file_path}')
                break
            fh = open(file_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download to {file_path}: {int(status.progress() * 100)}%")
            fh.close()
            break
        except:
            print('Failed to download! Trying again...')
            rm(file_path)
            this_try += 1
            continue
    
    if this_try >= num_tries:
        print(f'Failed at {file_path}')
        gc['failed'].append(file_path)

def gdrive_down(url, dl_path, credentials_path='/work/awilf/utils/gdrive_credentials.json', token_path='/work/awilf/utils/gdrive_token.json', max_files=1000, num_tries=3):
    '''
    This function can be used on url's that refer to a google drive folder or a google drive file.

    If using for a folder, dl_path can either be
        the path to a directory that exists.  If so, a new folder with the same name as on google drive will be created within dl_path.
        the path to a directory that does not exist.  If this is the case, this will be the path that we write files within.

    If using for a file, dl_path can either be
        the path to a directory that exists.  In this case, the file will be written in join(dl_path, filename)
        the path to a file (a path containing .).  In this case, the file will be written here.

    max_files: max number of files to download per folder (required param to gdrive)

    e.g. 
    folder_url = 'https://drive.google.com/drive/folders/1VVyFjq5Q6fk_R-oTTtR4t_58QQyV4aJt?usp=sharing'
    file_url = 'https://drive.google.com/file/d/1xYxU7ViEY5xODkwY7FllKPxa4tjfuXwM/view?usp=sharing'
    '''
    service = get_service(credentials_path, token_path)

    ## get id: assumes all hashes are 33 characters long and there are no others path elements with 33 chars
    try:
        url = url.replace('open?', '').replace('id=','')
        this_id = lfilter(lambda elt: len(elt)==33, url.split('/'))[0]
    except:
        assert False, f'Check download url below.  The hash length must be 33.  If not, find a different way to get the hash from the url. \n{url}'

    if 'folders' in url:
        folder_id = this_id

        if exists(dl_path) and isdir(dl_path):
            folder_name = service.files().get(fileId=folder_id).execute()['name']
            dl_path = join(dl_path, folder_name)
        mkdirp(dl_path)
        
        # list files, download each
        files = service.files().list(q= f"mimeType != 'application/vnd.google-apps.folder' and '{folder_id}' in parents", pageSize=max_files, fields="*").execute()
        print(f'Downloading files from folder {rsp(dl_path)}')
        for file in tqdm(files['files']):
            try:
                download_file(file['id'], file_path=join(dl_path, file['name']), service=service, num_tries=num_tries)
            except:
                hi=2
                assert False
        
        # list subfolders, recurse this function on each url where path is now the folder path
        folders = service.files().list(q= f"mimeType = 'application/vnd.google-apps.folder' and '{folder_id}' in parents", pageSize=max_files, fields="*").execute()
        for folder in folders['files']:
            print(f'Recursing on folder {folder["name"]}')
            new_url = f'https://drive.google.com/drive/folders/{folder["id"]}?usp=sharing'
            new_dl_path = join(dl_path, folder['name'])
            gdrive_down(new_url, new_dl_path, credentials_path=credentials_path, token_path=token_path, max_files=max_files)
    else:
        url = url.replace('?usp=sharing', '').replace('/view', '')
        file_id = rsp(url).split('?')[0]
        download_file(file_id, file_path=dl_path, service=service, num_tries=num_tries)


defaults = [
    ('--mode', str, 'up'), # upload or download
    
    # upload
    ('--folder_id', str, IMMORTAL_FOLDER_ID), # optional
    ('--file_list', str, ''), # nonoptional
    ('--creds_path', str, '/work/awilf/utils/gdrive_credentials.json'),
    ('--token_path', str, '/work/awilf/utils/gdrive_token.json'),
    ('--rm_after', int, 0), # whether to remove file after uploading successfully

    # download
    ('--url', str, ''),
    ('--dl_path', str, ''), # should be a FILEPATH, not a directory path
    ('--num_tries', int, 3), # should be a FILEPATH, not a directory path
    ('--skip_existing', int, 1), # should be a FILEPATH, not a directory path
]

def main(_gc):
    global gc
    gc = _gc
    gc['failed'] = [] # failed to download, print msg at end
    
    if gc['mode'] == 'up':
        file_list = gc['file_list']
        assert file_list != ''
        file_list = file_list.split(',')
        gdrive_up(file_list, gc['folder_id'], credentials_path=gc['creds_path'], token_path=gc['token_path'], rm_after=gc['rm_after'])
    
    elif gc['mode'] == 'down':
        assert gc['url'] != '', 'url must be non empty'
        assert gc['dl_path'] != '', 'dl_path must be non empty'
        gdrive_down(gc['url'], dl_path=gc['dl_path'], credentials_path=gc['creds_path'], token_path=gc['token_path'], num_tries=gc['num_tries'])
        if len(gc['failed']) > 0:
            print('Some files failed:', gc['failed'])

if __name__ == '__main__':
    '''
    e.g.
    Up
        p /work/awilf/utils/gdrive.py --mode up --file_list hi.txt,yo.txt
        p /work/awilf/utils/gdrive.py --mode up --file_list hi.txt,yo.txt --rm_after 1 --folder_id 127KXMyU5Zm0P5RpJINcx5e5jmfCntw5b

    Down
        p /work/awilf/utils/gdrive.py --mode down --url https://drive.google.com/file/d/1kDutUqR9taJgL_1klxWkHYB-YFRkPJDx/view?usp=sharing --dl_path delete/yo.txt

        ## URL is a file
            # dl_path is filepath
            p gdrive.py --mode down --url https://drive.google.com/file/d/1GsxlTEtW65DyXXAno_-JDPlji1FoJsNN/view?usp=sharing --dl_path ./test.txt
            rm test.txt

            # dl_path is folder that exists
            mkdir -p test
            p gdrive.py --mode down --url https://drive.google.com/file/d/1GsxlTEtW65DyXXAno_-JDPlji1FoJsNN/view?usp=sharing --dl_path ./test
        
        ## URL is a folder
            # dl_path is folder that exists
            rm -rf test && mkdir -p test
            p gdrive.py --mode down --url https://drive.google.com/drive/folders/1VVyFjq5Q6fk_R-oTTtR4t_58QQyV4aJt?usp=sharing --dl_path ./test

            # dl_path is folder that does not exist
            p gdrive.py --mode down --url https://drive.google.com/drive/folders/1VVyFjq5Q6fk_R-oTTtR4t_58QQyV4aJt?usp=sharing --dl_path test2
            rm -rf test2
    '''
    main_wrapper(main,defaults,results=False)

    # gc = {k.split('--')[1]: v for k,_,v in defaults}
    # gc['mode'] = 'up'
    # gc['rm_after']
    # gc['folder_id'] = '127KXMyU5Zm0P5RpJINcx5e5jmfCntw5b'
    # gc['file_list'] = '/work/awilf/hi/hi.txt,/work/awilf/hi/yo.txt'
    # main(gc)

