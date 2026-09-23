"""Prime numbers output module.

本文件用于根据输入的正整数 num，输出 num 以内的所有质数。
"""


def is_prime(n):
	"""判断一个数是否为质数。

	参数:
		n (int): 需要判断的整数。

	返回:
		bool: 如果 n 是质数返回 True，否则返回 False。
	"""
	if n < 2:
		return False
	for i in range(2, int(n ** 0.5) + 1):
		if n % i == 0:
			return False
	return True


def print_prime_numbers(num):
	"""输出 num 以内的所有质数。

	参数:
		num (int): 质数的上限，必须是大于等于 2 的整数。

	返回:
		list: 返回 num 以内的质数列表。
	"""
	primes = [n for n in range(2, num + 1) if is_prime(n)]
	print(" ".join(str(prime) for prime in primes))
	return primes


def main():
	"""从用户输入读取 num，并输出 num 以内的质数。

	参数:
		无

	返回:
		None
	"""
	try:
		num = int(input("Please enter num: "))
		if num < 2:
			print("There is no prime number within num.")
			return
		print_prime_numbers(num)
	except ValueError:
		print("Please enter a valid integer.")


if __name__ == "__main__":
	main()

# 示例输入:
# 20
#
# 示例输出:
# 2 3 5 7 11 13 17 19
