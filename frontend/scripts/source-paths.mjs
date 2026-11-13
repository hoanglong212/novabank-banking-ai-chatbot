// Adobe's source-frame trace uses absolute M/C/Z contours. Keep its curves;
// do not substitute font glyphs or icon-library approximations for these paths.
export function svgContours(d, origin = [0, 0]) {
  const tokens = d.match(/[MCZ]|-?(?:\d*\.)?\d+(?:e[-+]?\d+)?/gi);
  const contours = [];
  let current, command, index = 0;
  const point = () => [Number(tokens[index++]) - origin[0], Number(tokens[index++]) - origin[1]];
  while (index < tokens.length) {
    if (/^[MCZ]$/i.test(tokens[index])) command = tokens[index++];
    if (command === 'M') {
      current = { v: [point()], i: [[0, 0]], o: [[0, 0]], c: false };
      contours.push(current);
    } else if (command === 'C') {
      const a = point(), b = point(), end = point(), last = current.v.at(-1);
      current.o[current.o.length - 1] = [a[0] - last[0], a[1] - last[1]];
      current.v.push(end); current.i.push([b[0] - end[0], b[1] - end[1]]); current.o.push([0, 0]);
    } else if (command === 'Z') {
      current.c = true;
      command = undefined;
    } else throw new Error(`Unsupported source path command: ${command}`);
  }
  return contours;
}
