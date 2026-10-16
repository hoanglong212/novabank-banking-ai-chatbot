"""Fictional sample knowledge base; no real-bank fees or policy statements."""
import re
import unicodedata

FAQ = [
    ('account', 'Mở tài khoản', 'Bạn có thể tìm hiểu quy trình mở tài khoản qua kênh chính thức của ngân hàng. NovaBank trong ứng dụng này là ngân hàng giả lập và không mở tài khoản thật.', ['mo tai khoan', 'open account', 'dang ky tai khoan']),
    ('card', 'Thẻ bị khóa', 'Nếu thẻ bị khóa, hãy liên hệ tổng đài chính thức hoặc tới chi nhánh ngân hàng phát hành để xác minh. Chatbot demo không thể mở khóa thẻ thật.', ['the bi khoa', 'khoa the', 'atm', 'card blocked']),
    ('vietqr', 'VietQR', 'VietQR hỗ trợ thể hiện thông tin phục vụ thanh toán/chuyển khoản bằng mã QR. Luôn xác nhận tên người nhận, số tiền và ngân hàng trong ứng dụng chính thức trước khi đồng ý chuyển tiền.', ['vietqr', 'qr', 'ma qr', 'quet ma']),
    ('transfer', 'Chuyển khoản', 'Bạn nên kiểm tra người thụ hưởng, hạn mức và trạng thái giao dịch trong ứng dụng ngân hàng chính thức. Phí và hạn mức phụ thuộc ngân hàng và loại tài khoản.', ['chuyen tien', 'chuyen khoan', 'transfer', 'han muc', 'phi chuyen']),
    ('fraud', 'Phòng tránh lừa đảo', 'Không cung cấp mật khẩu, OTP, mã PIN hoặc mã khôi phục cho chatbot hay người lạ. Nếu nghi lừa đảo, liên hệ ngân hàng qua kênh chính thức.', ['lua dao', 'otp', 'pin', 'bao mat', 'mat tien']),
    ('hours', 'Giờ làm việc', 'Giờ giao dịch khác nhau theo chi nhánh và ngân hàng. Hãy kiểm tra website chính thức của ngân hàng bạn đang sử dụng.', ['gio lam viec', 'chi nhanh', 'branch', 'working hours']),
    ('transaction', 'Giao dịch chậm', 'Nếu chuyển khoản chưa tới, hãy lưu mã tham chiếu, đối chiếu trạng thái trong ứng dụng và liên hệ hỗ trợ chính thức. Ứng dụng này chỉ có giao dịch mô phỏng.', ['giao dich loi', 'chua nhan', 'pending', 'giao dich', 'cham tien']),
]


def fold(s: str) -> str:
    s = s.lower().replace('đ', 'd')
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def search(query: str):
    words = [w for w in re.findall(r'\w+', fold(query)) if len(w) > 2]
    found = []
    for key, title, answer, synonyms in FAQ:
        bag = fold(' '.join([key, title, *synonyms]))
        score = sum(1 for w in words if w in bag)
        if any(fold(synonym) in fold(query) for synonym in synonyms):
            score += 3
        if score:
            found.append((score, key, title, answer))
    found.sort(key=lambda x: x[0], reverse=True)
    if not found:
        return {'matches': [], 'notice': 'No approved sample-bank FAQ answer found. Do not invent a fee, limit or bank rule.'}
    return {'matches': [{'id': k, 'title': t, 'answer': a} for _, k, t, a in found[:2]], 'notice': 'All NovaBank FAQ data is fictional demonstration material.'}
