def exponential_moving_average(values, alpha=0.1):
    # Computes EMA for a list of values
    ema = values[0]
    for value in values[1:]:
        ema = alpha * value + (1 - alpha) * ema
    return ema

def predict_with_ema(track, predict_time_ms, alpha=0.1):
    if len(track) < 2:
        return None  # Not enough data to predict

    predict_time_sec = predict_time_ms / 1000.0

    # Extract positions and times
    xs = [point[0] for point in track]
    ys = [point[1] for point in track]
    times = [point[2] for point in track]

    # Calculate velocity for each pair of points
    velocities_x = [(xs[i] - xs[i - 1]) / (times[i] - times[i - 1]) for i in range(1, len(xs))]
    velocities_y = [(ys[i] - ys[i - 1]) / (times[i] - times[i - 1]) for i in range(1, len(ys))]

    # Compute EMA for the velocities
    ema_vx = exponential_moving_average(velocities_x, alpha)
    ema_vy = exponential_moving_average(velocities_y, alpha)

    # Predict future position
    predicted_x = xs[-1] + ema_vx * predict_time_sec
    predicted_y = ys[-1] + ema_vy * predict_time_sec

    return predicted_x, predicted_y

