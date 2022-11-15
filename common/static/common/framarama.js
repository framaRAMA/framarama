
function cssRemove(el, clazz) {
  el.className = el.className.replace(new RegExp('\s*' + clazz), '');
}

function cssAdd(el, clazz) {
  cssRemove(el, clazz)
  el.className = el.className + ' ' + clazz;
}

