from decimal import Decimal
print(64.35*10**6)
amount_str = str("64.35")  # 或者让 reward 本身就是字符串
scale = Decimal(10) ** 6
amount = int(Decimal(amount_str) * scale)
print(amount)
