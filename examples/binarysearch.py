"""Binary Search implementation."""


def binary_search(arr: list, target) -> int:
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1


if __name__ == "__main__":
    data = [3, 9, 10, 27, 38, 43, 82]
    print(f"数组: {data}")
    print(f"查找 27: index={binary_search(data, 27)}")
    print(f"查找 50: index={binary_search(data, 50)}")
