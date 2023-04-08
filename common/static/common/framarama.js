
function cssRemove(el, clazz) {
  el.className = el.className.replace(new RegExp('\s*' + clazz), '');
}

function cssAdd(el, clazz) {
  cssRemove(el, clazz);
  el.className = el.className + ' ' + clazz;
}

function cssToggle(el, clazz) {
  if (el.className.indexOf(clazz) != -1) {
    cssRemove(el, clazz);
  } else {
    cssAdd(el, clazz);
  }
}
