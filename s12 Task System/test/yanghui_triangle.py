"""杨辉三角输出模块。

本文件用于根据输入的层数生成并打印杨辉三角。
"""


def print_yanghui_triangle(levels):
	"""打印杨辉三角。

	参数:
		levels (int): 杨辉三角的层数，必须是正整数。

	返回:
		None: 该函数只打印杨辉三角，不返回任何值。
	"""
	if levels <= 0:
		return

	triangle = []
	for i in range(levels):
		row = [1]
		if triangle:
			last_row = triangle[-1]
			for j in range(len(last_row) - 1):
				row.append(last_row[j] + last_row[j + 1])
			row.append(1)
		triangle.append(row)

	last_line = " ".join(str(num) for num in triangle[-1])
	width = len(last_line)

	for row in triangle:
		line = " ".join(str(num) for num in row)
		print(line.center(width))


def main():
	"""从用户输入读取层数，并打印杨辉三角。

	参数:
		无

	返回:
		None
	"""
	try:
		levels = int(input("Please enter the number of levels: "))
		if levels <= 0:
			print("The number of levels must be a positive integer.")
			return
		print_yanghui_triangle(levels)
	except ValueError:
		print("Please enter a valid integer.")


if __name__ == "__main__":
	main()

# 示例输入:
# 5
#
# 示例输出:
#     1
#    1 1
#   1 2 1
#  1 3 3 1
# 1 4 6 4 1
