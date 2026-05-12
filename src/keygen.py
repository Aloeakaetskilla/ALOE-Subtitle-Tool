"""激活码生成器 - 管理员工具

用法:
    python keygen.py <机器码>

示例:
    python keygen.py A1B2C3D4E5F6G7H8
"""
import sys
from license import generate_activation_code


def main():
    if len(sys.argv) < 2:
        print("=" * 50)
        print("ALOE字幕提取软件 - 激活码生成器")
        print("=" * 50)
        print()
        machine_id = input("请输入用户的机器码: ").strip()
    else:
        machine_id = sys.argv[1].strip()

    if not machine_id:
        print("错误：机器码不能为空")
        return

    code = generate_activation_code(machine_id)
    print()
    print(f"机器码: {machine_id}")
    print(f"激活码: {code}")
    print()
    print("请将激活码发送给用户。")


if __name__ == "__main__":
    main()
