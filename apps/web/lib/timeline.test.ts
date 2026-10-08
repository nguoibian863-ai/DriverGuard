import test from "node:test";
import assert from "node:assert/strict";
import { downsample, pruneOlderThan, levelBand } from "./timeline.ts";

test("downsample giữ đầu/cuối, đúng giới hạn và thứ tự", () => {
  assert.deepEqual(downsample([0, 1, 2, 3, 4, 5], 3), [0, 3, 5]);
  assert.deepEqual(downsample([0, 1], 3), [0, 1]);
  assert.deepEqual(downsample([0, 1], 1), [1]);
  assert.deepEqual(downsample([0, 1], 0), []);
});

test("pruneOlderThan giữ điểm đúng ranh giới 5 phút", () => {
  const points = [{ time: 699 }, { time: 700 }, { time: 999 }, { time: 1001 }];
  assert.deepEqual(pruneOlderThan(points, 1000, 300), [{ time: 700 }, { time: 999 }]);
});

test("levelBand phân mức tại ngưỡng 40 và 70", () => {
  assert.equal(levelBand(39.99), "NORMAL");
  assert.equal(levelBand(40), "WARNING");
  assert.equal(levelBand(69.99), "WARNING");
  assert.equal(levelBand(70), "DANGER");
});
