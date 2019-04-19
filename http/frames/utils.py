def get_chunks(data, chunk_size):
    chunk_start = 0
    chunk_end = chunk_size
    last_index = len(data) / chunk_size
    
    if len(data) / chunk_size > 0:
        if len(data) % chunk_size > 0:
            last_index += 1
        else:
            last_index -= 1

    counter = 0
    while chunk_end < len(data) + chunk_size:
        yield data[chunk_start:chunk_end], counter == last_index
        chunk_start += chunk_size
        chunk_end += chunk_size
        counter += 1