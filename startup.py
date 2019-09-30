import sys
import argparse
import os
from os import listdir
from os.path import isfile, join
from update import UpdateStatus, Extension, Pattern, Infos
import subprocess
import concurrent.futures
import urllib3
import shelve
import json
from sty import fg, bg, ef, rs

user_agent = {'user-agent': 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) ..'}
http = urllib3.PoolManager(headers=user_agent)

# Update
folders_to_update = []
current_folder = ''

args = any
thread_url = ''
thread_id = ''
update_needed = False
download_path = 'downloads'
extensions = []
files_dict = {}
missing_files_dict = {}
max_workers = os.cpu_count() * 5


# TODO: ask for a default folder & save path

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--thread_url')
    parser.add_argument('-e', '--file_extension', action='append', nargs='+')
    parser.add_argument('-c', '--check_update')
    parser.add_argument('-v', '--version')

    global args, update_needed
    args = parser.parse_args()
    if args.check_update is not None:
        update_needed = True


def check_arguments_validity():
    global thread_url, extensions, update_needed

    thread_url = args.thread_url
    extensions = args.file_extension
    update = args.check_update

    # If update is not None => Asked
    if update is not None:
        update_needed = True
        return

    if thread_url is None:
        print('Specify the thread URL (e.g. -u http://boards.4chan.org/gif/thread/8728832783787)')
        help_cli()
        sys.exit()
    if extensions is None:
        print('Specify which extension do you want (e.g. -e webm)')
        help_cli()
        sys.exit()


def download_a_file(filename):
    request = http.request('GET',
                           f'{files_dict[filename]}')

    with open(f'{download_path}/{thread_id}/{filename}', 'wb') as out:
        out.write(request.data)
        print(f'\t~ {filename} saved')


def help_cli():
    print("""
    
    Command line arguments : 
    -u, --thread_url=           Specify the thread URL (e.g. http://boards.4chan.org/gif/thread/8728832783787)
    -e, --file_extension=       Specify which extension do you want (e.g. webm|jpg|gif)
    -c, --check_update          Check if your data needs an update (e.g. -c yes)
    -v, --version=              4Chan downloader version
    -h, --help=                 Show help

    """)


def create_folder_if_not_exist(name):
    # Create a thread folder with it id
    # Create directory if not exist
    if not os.path.exists(name):
        os.makedirs(name)
        print(f'-> Directory {name} created.')


def async_download(status):
    files = []

    if status == UpdateStatus.FIRST_DOWNLOAD:
        files = list(dict.fromkeys(files_dict))
    if status == UpdateStatus.NEEDED:
        files = list(dict.fromkeys(missing_files_dict))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for _ in executor.map(download_a_file, files):
            pass


def find_files():
    global files_dict

    # Get HTML sources
    request = http.request('GET',
                           f'{thread_url}')

    html_sources = str(request.data)

    # Extension asked by user in arguments
    # For each extensions handle by this script, we search if the user asked for one, or many, of them
    urls_webm = []
    urls_gif = []
    for ext in extensions:
        if ext[0] == Extension.WEBM.value:
            urls_webm = list(dict.fromkeys(Pattern.WEBM.value.findall(html_sources)))
        if ext[0] == Extension.GIF.value:
            urls_gif = list(dict.fromkeys(Pattern.GIF.value.findall(html_sources)))

    # Merge all lists together
    lists_merged = urls_webm + urls_gif

    # Search for other types
    print(f'{len(lists_merged)} files found in the original thread !')

    if len(lists_merged) == 0:
        print('\nNo file available in this thread...')
        sys.exit()

    # Make a dictionnary {'filename': 'url'}
    filename_regex = Pattern.FILENAME.value

    for url in lists_merged:
        # Extract filename for key
        filename = filename_regex.findall(url)
        # Add to dict
        files_dict[filename[0]] = url

    need_update = check_if_folder_already_exist()

    if need_update == UpdateStatus.NOT_NEEDED:
        # Directory and files already exists, no update needed
        print('\t-> Everything seems to be up to date here !\n')
    elif need_update == UpdateStatus.NEEDED:
        # Directory and files already exists, update needed
        user_choice = input(
            fg.green + f'\n{len(missing_files_dict)} new file(s) available, do you want to update your folder ? [Y/n] ' + fg.rs)
        if user_choice == '' or user_choice == 'y' or user_choice == 'Y' or user_choice == 'yes':
            # Async call
            async_download(UpdateStatus.NEEDED)
        else:
            print('No download. Good bye ;)')
            sys.exit()
    elif need_update == UpdateStatus.FIRST_DOWNLOAD:
        # Directory and files doens't exists
        user_choice = input(fg.green + f'\nDo you want to download this {len(files_dict)} files ? [Y/n]' + fg.rs)
        if user_choice == '' or user_choice == 'y' or user_choice == 'Y' or user_choice == 'yes':
            create_folder_if_not_exist(f'{download_path}/{thread_id}')
            # Async call
            async_download(UpdateStatus.FIRST_DOWNLOAD)
        else:
            print('No download. Good bye ;)')
            sys.exit()


def check_if_folder_already_exist():
    # Extract thread id
    global thread_id, files_dict, missing_files_dict
    thread_id = thread_url.split('/')[-1]

    try:
        local_files = [f for f in listdir(f'{download_path}/{thread_id}') if
                       isfile(join(f'{download_path}/{thread_id}', f))]
    except FileNotFoundError:
        # Directory doesn't exist yet -> First download
        return UpdateStatus.FIRST_DOWNLOAD

    thread_files = list(files_dict.keys())

    if not local_files:
        # Nothing exist locally
        return UpdateStatus.FIRST_DOWNLOAD

    # Difference between two lists
    diff_files_missing = list(set(thread_files).difference(set(local_files)))

    # Update missing files dictionary
    for missing_file in diff_files_missing:
        missing_files_dict[missing_file] = files_dict[missing_file]

    # Check if it's necessary to download files
    if len(missing_files_dict) == 0:
        return UpdateStatus.NOT_NEEDED

    return UpdateStatus.NEEDED


# Open the current folder used
def ask_to_open_folder():
    open_current_folder = input(f'\nDo you want to open folder ? [Y/n]')
    if open_current_folder == '' or open_current_folder == 'y' or open_current_folder == 'Y' \
            or open_current_folder == 'yes':
        subprocess.Popen('open {}'.format(f'{download_path}/{thread_id}'), shell=True)
    else:
        print('\nOkay ! Enjoy :)')
        sys.exit()


def intro():
    print("""
    
____________/\\\\\___________________/\\\\\______________________________________        
 __________/\\\\\\\\\__________________\/\\\\\______________________________________       
  ________/\\\\\/\\\\\__________________\/\\\\\______________________________________      
   ______/\\\\\/\/\\\\\________/\\\\\\\\\\\\\\\\_\/\\\\\__________/\\\\\\\\\\\\\\\\\_____/\\\\/\\\\\\\\\\\\___     
    ____/\\\\\/__\/\\\\\______/\\\\\//////__\/\\\\\\\\\\\\\\\\\\\\__\////////\\\\\___\/\\\\\////\\\\\__    
     __/\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\__/\\\\\_________\/\\\\\/////\\\\\___/\\\\\\\\\\\\\\\\\\\\__\/\\\\\__\//\\\\\_   
      _\///////////\\\\\//__\//\\\\\________\/\\\\\___\/\\\\\__/\\\\\/////\\\\\__\/\\\\\___\/\\\\\_  
       ___________\/\\\\\_____\///\\\\\\\\\\\\\\\\_\/\\\\\___\/\\\\\_\//\\\\\\\\\\\\\\\\/\\\\_\/\\\\\___\/\\\\\_ 
        ___________\///________\////////__\///____\///___\////////\//__\///____\///__ (downloader)

    """)


def load_previous_config():
    # https://docs.python.org/2/library/shelve.html
    d = shelve.open('persist')
    d['test'] = 'Bonjour les gens'
    data = d['test']
    print(data)
    d.close()


def scan_existing_files():
    global folders_to_update
    # Extract directories list
    folders_to_update = os.listdir(download_path)

    # Remove macos files
    if folders_to_update.__contains__('.DS_Store'):
        folders_to_update.remove('.DS_Store')

    if len(folders_to_update) == 0:
        print('No existing directory in downloads...')
        sys.exit()

    print(f'Check updates on {len(folders_to_update)} folder(s).')


def create_main_folder():
    create_folder_if_not_exist(download_path)


def backup_informations():
    # Create object to save all informations about download done
    infos = Infos(thread_url, thread_id, extensions, files_dict)
    # Create a JSON object
    infos_json = json.dumps(infos.__dict__, indent=4)

    with open(f'{download_path}/{thread_id}/info.txt', 'wb') as out:
        out.write(infos_json.encode())  # Encode to str to Bytes


def update_instance_variables(folder_name):
    global thread_id, thread_url, update_needed, extensions, files_dict, missing_files_dict

    with open(f'{download_path}/{folder_name}/info.txt', 'rb') as infos:
        test = infos.read()
        current_informations = json.loads(test)

    # Update variables
    thread_url = current_informations['url']
    thread_id = current_informations['thread_id']
    extensions = current_informations['extensions']
    files_dict = current_informations['files']


def clean_instance_variables():
    global thread_id, thread_url, update_needed, extensions, files_dict, missing_files_dict
    # Reset all instances variables to default values
    thread_url = ''
    thread_id = ''
    update_needed = False
    extensions = []
    files_dict = {}
    missing_files_dict = {}


def backup_informations_available(folder_name):
    files = os.listdir(f'{download_path}/{folder_name}')
    if not files.__contains__('info.txt'):
        return False
    return True


def update_folders():
    for folder in folders_to_update:
        backup_data = backup_informations_available(folder)
        if backup_data:
            update_instance_variables(folder)
            print('\n--------------------------')
            print(f'o Check folder {folder}:')
            find_files()
            backup_informations()
            clean_instance_variables()


def main():
    intro()
    # load_previous_config()
    parse_arguments()
    check_arguments_validity()
    create_main_folder()
    if update_needed:
        scan_existing_files()
        update_folders()
        print('All updates are done ! Good bye.')
    else:
        print('------------------------------')
        print('Begin')
        print('------------------------------')
        find_files()
        backup_informations()
        ask_to_open_folder()
        print('------------------------------')
        print('All files have been downloaded')
        print('------------------------------')


if __name__ == '__main__':
    main()
