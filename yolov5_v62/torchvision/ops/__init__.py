import torch

def nms(boxes, scores, iou_threshold):
    keep = []
    idxs = scores.argsort(descending=True)

    while idxs.numel() > 0:
        cur = idxs[0]
        keep.append(cur)

        if idxs.numel() == 1:
            break

        cur_box = boxes[cur].unsqueeze(0)
        rest = boxes[idxs[1:]]

        xx1 = torch.maximum(cur_box[:, 0], rest[:, 0])
        yy1 = torch.maximum(cur_box[:, 1], rest[:, 1])
        xx2 = torch.minimum(cur_box[:, 2], rest[:, 2])
        yy2 = torch.minimum(cur_box[:, 3], rest[:, 3])

        inter = (xx2 - xx1).clamp(0) * (yy2 - yy1).clamp(0)
        area1 = (cur_box[:, 2] - cur_box[:, 0]) * (cur_box[:, 3] - cur_box[:, 1])
        area2 = (rest[:, 2] - rest[:, 0]) * (rest[:, 3] - rest[:, 1])

        iou = inter / (area1 + area2 - inter + 1e-6)
        idxs = idxs[1:][iou <= iou_threshold]

    if len(keep):
        return torch.stack(keep)
    return torch.empty((0,), dtype=torch.long, device=boxes.device)
