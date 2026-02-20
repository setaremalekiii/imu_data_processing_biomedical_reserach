% Example Workflow Outline
vidReader = VideoReader('video.mp4');
tracker = vision.PointTracker('MaxBidirectionalError', 2);
% ... (initialize with initialLocation) ...
while hasFrame(vidReader)
    frame = readFrame(vidReader);
    [points, validity] = tracker(frame);
    % Store positions
    positions = [positions; points(validity, :)];
end
