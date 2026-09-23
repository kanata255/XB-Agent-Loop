"""斐波那契数组测试用例。

本文件用于生成并打印斐波那契数列的前 N 项数组，作为斐波那契数组的测试用例。
"""


def fibonacci_array(n):
	"""生成斐波那契数组。

	参数:
		n (int): 需要生成的斐波那契数列项数。

	返回:
		list: 前 n 项斐波那契数列组成的数组。
	"""
	if n <= 0:
		return []
	if n == 1:
		return [0]

	result = [0, 1]
	for _ in range(2, n):
		result.append(result[-1] + result[-2])
	return result


def main():
	"""读取用户输入的项数，并打印对应的斐波那契数组。

	参数:
		无

	返回:
		None
	"""
	try:
		n = int(input("Please enter the number of terms: "))
		if n <= 0:
			print("The number of terms must be a positive integer.")
			return
		print(f"The first {n} terms of the Fibonacci sequence: {fibonacci_array(n)}")
	except ValueError:
		print("Please enter a valid integer.")


if __name__ == "__main__":
	main()

# 示例输入:
# 10
#
# 示例输出:
# The first 10 terms of the Fibonacci sequence: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
