// Construction pure du menu lateral : filtrage par role + regroupement en sous-menus.
// items : [{ path, labelKey, icon, roles, group?, adminHidden?, separator? }]
// groups : { [groupKey]: { labelKey, icon } }
// Retourne une liste d'entrees :
//   { type: 'link', item }  ou  { type: 'group', key, labelKey, icon, children: [item] }
// L'admin voit tout sauf les items marques adminHidden.

export function visibleItems(items, { isAdmin, hasRole }) {
    if (isAdmin) return items.filter((i) => !i.adminHidden);
    return items.filter((i) => i.roles && hasRole(i.roles));
}

export function buildMenu(items, { isAdmin, hasRole, groups = {} }) {
    const visible = visibleItems(items, { isAdmin, hasRole });
    const entries = [];
    const groupEntries = {};
    for (const item of visible) {
        if (!item.group) {
            entries.push({ type: 'link', item });
            continue;
        }
        let g = groupEntries[item.group];
        if (!g) {
            const meta = groups[item.group] || {};
            g = { type: 'group', key: item.group, labelKey: meta.labelKey, icon: meta.icon, children: [] };
            groupEntries[item.group] = g;
            entries.push(g); // le groupe prend la place de son premier enfant
        }
        g.children.push(item);
    }
    // Un seul enfant visible : lien plat, pas de parent.
    return entries.map((e) => (e.type === 'group' && e.children.length === 1
        ? { type: 'link', item: e.children[0] }
        : e));
}

export function groupContainsPath(group, path) {
    return group.children.some((c) => path.includes(c.path));
}
