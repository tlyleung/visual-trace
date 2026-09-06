def bubble_sort(nums: list[int]) -> list[int]:
    for i in range(len(nums)):
        for j in range(len(nums) - i - 1):
            if nums[j] > nums[j + 1]:
                nums[j], nums[j + 1] = nums[j + 1], nums[j]
    return nums


def main():
    args = ([4, 2, 5, 1],)
    func = bubble_sort
    return func, args


if __name__ == "__main__":
    func, args = main()
    print(func(*args))
