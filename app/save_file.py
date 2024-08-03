from datetime import datetime

class SaveFile():
    def save(source, buffer):
        now = datetime.now()
        output_file = f'output/cam_{source}_{now.strftime("%Y%m%d_%H%M%S")}'
        with open(output_file, 'wb') as video_file:
            for frame in buffer:
                video_file.write(frame.data)