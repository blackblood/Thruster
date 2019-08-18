def get_chunks(data, chunk_size, offset=0):
    data_length = len(data) - offset
    chunk_start = offset
    chunk_end = chunk_start + chunk_size
    last_index = data_length // chunk_size

    if data_length % chunk_size == 0:
        last_index -= 1

    counter = 0
    while chunk_end < len(data) + chunk_size:
        yield data[chunk_start:chunk_end], counter == last_index
        chunk_start += chunk_size
        chunk_end += chunk_size
        counter += 1
