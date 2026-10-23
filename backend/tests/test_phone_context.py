import pytest


@pytest.mark.parametrize('text',[
    'Số tiền 0987654321 VND', 'Chuyển 0972345678 đồng',
    'so tien: 0963456789', 'Amount: 0954567890',
    'Thanh toán 0945678901 đ', 'Giá 0936789012 ₫',
])
def test_money_is_not_phone(text):
    from app.pii_patterns import phone_entities
    assert phone_entities(text) == []


@pytest.mark.parametrize('text,expected',[
    ('Điện thoại: 0987654321','0987654321'),
    ('Liên hệ +84 934 567 890','+84 934 567 890'),
    ('SĐT 097-234-5678','097-234-5678'),
    ('Chuyển tiền rồi gọi số điện thoại 0963456789','0963456789'),
    ('Số tiền 0954567890 VND, SĐT 0945678901','0945678901'),
])
def test_phone_preserved_in_phone_context(text,expected):
    from app.pii_patterns import phone_entities
    hits = phone_entities(text)
    assert [text[h.start:h.end] for h in hits] == [expected]
