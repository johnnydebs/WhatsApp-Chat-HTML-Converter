import os
import html
import glob
from datetime import datetime

def detect_date_format(timestamps):
    formats = [
        '%d/%m/%Y, %H:%M:%S',
        '%m/%d/%Y, %H:%M:%S',
        '%Y/%m/%d, %H:%M:%S',
        '%d/%m/%Y, %H:%M',
        '%m/%d/%Y, %H:%M',
        '%Y/%m/%d, %H:%M'
    ]
    for fmt in formats:
        valid_count = 0
        for timestamp_str in timestamps:
            try:
                datetime.strptime(timestamp_str, fmt)
                valid_count += 1
            except ValueError:
                pass
        if valid_count == len(timestamps):
            return fmt
    return None

def extract_timestamps(lines):
    timestamps = []
    for line in lines:
        line = line.strip().replace('\u200e', '').replace('\u202f','')
        if line.startswith("[") and "]" in line:
            timestamp_str = line.split('] ', 1)[0].replace('[','')
            timestamps.append(timestamp_str)
    return timestamps

def process_message(message_lines, last_sender, date_format):
    first_line = message_lines[0].strip().replace('\u200e', '').replace('\u202f','')
    rest_of_message = "\n".join(message_lines[1:]).strip()

    # if first_line.startswith(tuple(f'{m}/' for m in range(1, 13))) and ' - ' in first_line and ': ' in first_line:
    if first_line.startswith("[") and "]" in first_line:
        timestamp_str, content = first_line.split('] ', 1)
        timestamp_str = timestamp_str.replace('[','')
        try:
            timestamp = datetime.strptime(timestamp_str, date_format)
            if content.startswith('.:'):
                sender = 'Me'
                message = content[3:]
            else:
                sender, message = content.split(': ', 1)
            message = f"{message}\n{rest_of_message}" if rest_of_message else message
        except ValueError:
            timestamp, timestamp_str, sender, message = None, '', last_sender, first_line + "\n" + rest_of_message if rest_of_message else first_line
    else:
        timestamp, timestamp_str, sender, message = None, '', last_sender, first_line + "\n" + rest_of_message if rest_of_message else first_line

    return timestamp, sender.strip(), message.strip(), timestamp_str

def is_image(file_name):
    return file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))

def is_audio(file_name):
    return file_name.lower().endswith(('.mp3', '.wav', '.ogg', '.opus'))

def is_video(file_name):
    return file_name.lower().endswith(('.mp4', '.avi', '.mov', '.wmv'))

def is_pdf(file_name):
    return file_name.lower().endswith('.pdf')

def create_media_embed(message, subfolder, senderclass):
    if message.lower() == 'null':
        # Determine call icon based on senderclass
        call_icon = '📞 Incoming call' if senderclass == 'other' else '📞 Outgoing call'
        return f'<div class="call-icon">{call_icon}</div>'
    # if '(file attached)' in message:
    #     file_name = message.split(' (file attached)')[0]
    #     file_path = html.escape(os.path.join(subfolder, file_name))
    if '<attached:' in message:
        file_name = message.split('<attached: ')[1].split('>')[0]
        file_path = html.escape(os.path.join(subfolder, file_name))
        if is_image(file_name):
            return f'<img src="{file_path}" alt="{file_name}" style="max-width: 100%;">'
        elif is_audio(file_name):
            return f'<audio controls><source src="{file_path}" type="audio/mpeg">Your browser does not support the audio element.</audio>'
        elif is_video(file_name):
            return f'<video controls><source src="{file_path}" type="video/mp4">Your browser does not support the video tag.</video>'
        elif is_pdf(file_name):
            return f'''
<object data="{file_path}" type="application/pdf" width="450px" height="700px">
    <p>Unable to display PDF file. <a href="{file_path}">Download</a> instead.</p>
</object>
'''
        else:
            return f'<a href="{file_path}">{html.escape(file_name)}</a> (file attached)'
    return html.escape(message).replace('\n', '<br>')

def get_next_version_number(folder_name):
    existing_files = glob.glob(f'{folder_name}_v*.html')
    max_version = -1
    for file in existing_files:
        version_part = os.path.basename(file).split('_v')[1]
        version_number = int(version_part.split('.html')[0])
        if version_number > max_version:
            max_version = version_number
    return max_version + 1

def get_message_start_lines(lines):
    start_lines = []
    for i, line in enumerate(lines):
        line = line.strip().replace('\u200e', '')
        # if line.startswith(tuple(f'{m}/' for m in range(1, 13))) and ' - ' in line and ': ' in line:
        if line.startswith("[") and "]" in line:
            start_lines.append(i)
    return start_lines

def main():
    subfolder = input("Enter the path to the subfolder containing the chat and media files: ").strip()
    
    # Sanitize user input for path traversal
    subfolder = os.path.abspath(subfolder)
    if not os.path.isdir(subfolder):
        print("Invalid folder path.")
        return

    folder_name = os.path.basename(os.path.normpath(subfolder))

    current_dir = os.getcwd()
    subfolder_path = os.path.join(current_dir, subfolder)  # Create full path
    parent_folder_name = os.path.basename(current_dir)
    # parent_folder_name = os.path.basename(os.path.dirname(os.path.normpath(subfolder)))

    # chat_file_path = os.path.join(subfolder, folder_name + '.txt')
    chat_file_path = os.path.join(subfolder, '_chat.txt')

    if not os.path.isfile(chat_file_path):
        print("Chat file not found.")
        return

    version_number = get_next_version_number(folder_name)
    output_html_path = f'{folder_name}_v{version_number}.html'

    with open(chat_file_path, 'r', encoding='utf-8') as chat_file:
        lines = chat_file.readlines()

    timestamps = extract_timestamps(lines)
    date_format = detect_date_format(timestamps)

    if not date_format:
        print("Could not detect timestamp format.")
        return

    start_lines = get_message_start_lines(lines)
    start_lines.append(len(lines))  # Add an endpoint for the last message

    html_content = '''
<html>
<head>
<meta charset="UTF-8">
<style>
body {font-family: Arial, sans-serif; margin: 0; padding: 10px; max-width: 1500px; margin: auto;}
.date {text-align: center; color: #555; margin: 20px 0;}
.bubble {border-radius: 20px; padding: 10px 20px; margin: 2px 10px; display: inline-block; max-width: 70%;}
.me {background-color: #DCF8C6; align-self: flex-end; text-align: right;}
.other {background-color: #E5E5EA; text-align: left;}
.sender {font-weight: bold;}
.timestamp {font-size: 0.8em; color: #999;}
.me .timestamp {text-align: right;}
.left {text-align: left;}
.right {text-align: right;}
.right .bubble {margin-left: auto; margin-right: 0;}
.left .bubble {margin-right: auto; margin-left: 0;}
</style>
<script>
function createSummary() {
    var selectedMessages = document.querySelectorAll('input[name="selected_messages"]:checked');
    var summaryContent = '<html><head><meta charset="UTF-8"><style>/* same CSS styles */</style></head><body>';

    selectedMessages.forEach(function(msg) {
        var messageDiv = msg.closest('.bubble').outerHTML;
        summaryContent += '<div class="bubble">' + messageDiv + '</div>';
    });

    summaryContent += '</body></html>';

    var summaryWindow = window.open('');
    summaryWindow.document.write(summaryContent);
    summaryWindow.document.close();
}
</script>
</head>
<body>
<!-- <button onclick="createSummary()">Create Summary</button><br/><br/> -->
'''

    last_date = None
    last_sender = 'Unknown'
    message_id = 0

    for i in range(len(start_lines) - 1):
        message_lines = lines[start_lines[i]:start_lines[i+1]]
        
        timestamp, sender, message, timestamp_str = process_message(message_lines, last_sender, date_format)
        
        if timestamp and sender:
            senderclass = 'me' if sender == 'Me' else 'other'

            message = create_media_embed(message, subfolder, senderclass)
            message_id += 1

            if timestamp and (last_date is None or timestamp.date() != last_date):
                html_content += f'<div class="date">{timestamp.strftime("%d %B %Y")}</div>'
                last_date = timestamp.date()

            alignment_class = 'right' if senderclass == 'me' else 'left'
            html_content += f'''
<div class="{alignment_class}">
    <div class="bubble {senderclass}">
        <!-- <input type="checkbox" id="msg_{message_id}" name="selected_messages" value="msg_{message_id}">
        <label for="msg_{message_id}"> -->
            <div class="sender">{html.escape(sender)}</div>
            {message}
            <div class="timestamp">{timestamp_str if timestamp else ''}</div>
        <!-- </label> -->
    </div>
</div>
'''
            last_sender = sender
        else:
            print("couldn't detect timestamp")

    html_content += '</body></html>'

    with open(output_html_path, 'w', encoding='utf-8') as output_file:
        output_file.write(html_content)

    print(f'HTML file created: {output_html_path}')

if __name__ == '__main__':
    main()
