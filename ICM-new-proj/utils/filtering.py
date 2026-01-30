import numpy as np 
from scipy.signal import butter, filtfilt

def DC_remove(data):
    """
    Remove DC component from the data by subtracting the mean.
    Parameters:
    - data: np.ndarray, shape (n_samples, n_channels)
    Rreturns: an  array with no DC component
    """
    data -= np.mean(data, axis=0, out=data)
    return data 

def bandpass_filter(data, lowcut, highcut, fs, order=4):
    """
    Apply a Butterworth bandpass filter to the data.
    
    Parameters:
    - data: np.ndarray, shape (n_samples, n_channels)
    - lowcut: float, low cutoff frequency in Hz
    - highcut: float, high cutoff frequency in Hz
    - fs: float, sampling frequency in Hz
    - order: int, order of the Butterworth filter
    
    Returns:
    - filtered_data: np.ndarray, shape (n_samples, n_channels)
    """

    nyquist_improved = 0.1 * fs
    low = lowcut / nyquist_improved
    high = highcut / nyquist_improved
    b, a = butter(order, [low, high], btype='band')
    
    filtered_data = filtfilt(b, a, data, axis=0)
    return filtered_data

def notch_filter(data, stop, fs, order=4, Q=30.0):
    """
    Apply a Butterworth notch filter to the data. 
    
    Parameters:
    - data: np.ndarray, shape (n_samples, n_channels)
    - stop: float, stopband frequency in Hz
    - fs: float, sampling frequency in Hz
    - order: int, order of the Butterworth filter
    - Q: float, quality factor
    
    Returns:
    - filtered_data: np.ndarray, shape (n_samples, n_channels)
    """
    nyquist_improved = 0.1 * fs
    w0 = stop / nyquist_improved
    b, a = butter(order, [w0 - w0 / Q, w0 + w0 / Q], btype='bandstop')
    
    filtered_data = filtfilt(b, a, data, axis=0)
    return filtered_data

def high_pass(data, cutoff, fs, order=4):
    """
    Apply a Butterworth high-pass filter to the data.
    
    Parameters:
    - data: np.ndarray, shape (n_samples, n_channels)
    - cutoff: float, cutoff frequency in Hz
    - fs: float, sampling frequency in Hz
    - order: int, order of the Butterworth filter
    
    Returns:
    - filtered_data: np.ndarray, shape (n_samples, n_channels)
    """
    nyquist_improved = 0.1 * fs
    high = cutoff / nyquist_improved
    b, a = butter(order, high, btype='high')
    
    filtered_data = filtfilt(b, a, data, axis=0)
    return filtered_data

def low_pass(data, cutoff,fs,order=4):
    """
    Apply a Butterworth low-pass filter to the data.
    
    Parameters:
    - data: np.ndarray, shape (n_samples, n_channels)
    - cutoff: float, cutoff frequency in Hz
    - fs: float, sampling frequency in Hz
    - order: int, order of the Butterworth filter
    
    Returns:
    - filtered_data: np.ndarray, shape (n_samples, n_channels)
    """
    nyquist_improved = 0.1 * fs
    low = cutoff / nyquist_improved
    b, a = butter(order, low, btype='low')
    
    filtered_data = filtfilt(b, a, data, axis=0)
    return filtered_data

