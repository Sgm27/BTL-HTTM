from transformers import VitsModel, AutoTokenizer
import torch
import numpy as np
from scipy.io.wavfile import write

# Load model + tokenizer
model = VitsModel.from_pretrained("facebook/mms-tts-vie").to("cuda")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")

# 📌 Một văn bản dài, không chia nhỏ
text = (
    "Trí tuệ nhân tạo, hay còn gọi là AI, đang ngày càng trở thành một phần không thể thiếu "
    "trong xã hội hiện đại. Nó xuất hiện trong điện thoại thông minh, trong các ứng dụng tìm kiếm, "
    "trong dịch vụ chăm sóc khách hàng và thậm chí trong cả lĩnh vực nghệ thuật sáng tạo. "
    "AI giúp các bác sĩ chẩn đoán bệnh nhanh hơn, giúp kỹ sư tối ưu hóa sản xuất, "
    "giúp giáo viên cá nhân hóa chương trình học cho từng học sinh. "
    "Trong ngành giao thông, AI hỗ trợ phát triển xe tự lái, giảm thiểu tai nạn và tắc đường. "
    "Trong tài chính, AI được sử dụng để phát hiện gian lận và phân tích rủi ro đầu tư. "
    "AI cũng đang mở ra những khả năng mới trong khoa học, như mô phỏng quá trình khám phá vũ trụ, "
    "nghiên cứu khí hậu toàn cầu và phát triển thuốc mới. "
    "Tuy nhiên, AI cũng đặt ra nhiều thách thức, bao gồm vấn đề quyền riêng tư, an ninh dữ liệu "
    "và sự thay đổi trong thị trường lao động. "
    "Chính vì vậy, việc phát triển AI cần đi kèm với các chính sách và quy định phù hợp "
    "để đảm bảo công nghệ này phục vụ lợi ích của toàn nhân loại. "
    "Với tốc độ phát triển nhanh chóng, AI hứa hẹn sẽ tiếp tục thay đổi căn bản cách con người "
    "sống, làm việc và tư duy trong thế kỷ 21."
)

# Encode nguyên văn bản
inputs = tokenizer(text, return_tensors="pt").to("cuda")

# Run inference
with torch.no_grad():
    output = model(**inputs).waveform

waveform = output.cpu().numpy().squeeze()  # shape (samples,)
sr = model.config.sampling_rate

# Hàm tạo chunk từ waveform
def audio_chunk_generator(waveform, chunk_size=16000*3):  
    """
    chunk_size: số samples mỗi chunk
    VD: sr*3 = 3 giây 1 chunk (nếu sr=16kHz thì ~48000 mẫu)
    """
    for i in range(0, len(waveform), chunk_size):
        yield waveform[i:i + chunk_size]

# Lưu từng chunk thành file audio riêng
for idx, chunk in enumerate(audio_chunk_generator(waveform, chunk_size=sr*3), start=1):
    filename = f"audio_chunk_{idx}.wav"
    write(filename, sr, chunk)
    print(f"Saved {filename}, length: {len(chunk)/sr:.2f} sec")
