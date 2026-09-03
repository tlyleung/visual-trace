from visual_trace.data_structures.list import List


def binary_search(nums: List[int], target: int) -> int:
    low = 0
    high = len(nums) - 1

    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            low = mid + 1
        else:
            high = mid - 1

    return -1


def main():
    args = (List(1, 3, 5, 7, 9, 11, 13), 11)
    func = binary_search
    return func, args


if __name__ == "__main__":
    func, args = main()
    print(func(*args))
