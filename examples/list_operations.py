def list_operations(nums: list[int]) -> int:
    test = 0
    nums.append(1)
    nums.append(2)
    nums.append(3)
    return nums


def main():
    args = ([-1, 0],)
    func = list_operations
    return func, args


if __name__ == "__main__":
    func, args = main()
    print(func(*args))
