// Existing search_sort.js content
document.addEventListener('DOMContentLoaded', function() {
    initializeTable('songs-table');
    initializeTable('songs-table-all');
    initializeTable('stats-table');
});

function initializeTable(tableId) {
    const searchBoxId = tableId === 'songs-table' ? 'search-box' : 'search-box-all';
    const searchBox = document.getElementById(searchBoxId);
    const table = document.getElementById(tableId);
    
    if (!table) {
        console.warn(`Table with id '${tableId}' not found.`);
        return;
    }
    
    let tableRows = Array.from(table.querySelectorAll('tbody tr'));
    const headers = table.querySelectorAll(`th.sortable[data-column]`);
    
    // Search functionality
    if (searchBox) {
        searchBox.addEventListener('keyup', function() {
            const searchTerm = searchBox.value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, "").trim();

            tableRows.forEach(function(row) {
                let searchText = row.getAttribute('data-search');
                if (searchText) {
                    searchText = searchText.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, "").trim();
                    if (searchText.indexOf(searchTerm) === -1) {
                        row.style.display = 'none';
                    } else {
                        row.style.display = '';
                    }
                }
            });

            applyStriping(table);
        });
    }
    
    // Sorting functionality
    headers.forEach(function(header) {
        header.addEventListener('click', function() {
            const column = header.getAttribute('data-column');
            let order = header.getAttribute('data-order') || 'asc';
            const isNumeric = ['Year Released', 'BPM'].includes(column);

            // Toggle the sorting order
            order = order === 'asc' ? 'desc' : 'asc';
            header.setAttribute('data-order', order);

            // Remove 'sorted' class from other headers and reset their data-order
            headers.forEach(h => {
                if (h !== header) {
                    h.classList.remove('sorted');
                    h.removeAttribute('data-order');
                }
            });

            // Add 'sorted' class to the active header
            header.classList.add('sorted');

            // Sort rows
            const sortedRows = tableRows.sort(function(a, b) {
                let aCell = a.querySelector(`td[data-column="${column}"]`);
                let bCell = b.querySelector(`td[data-column="${column}"]`);
                let aText = aCell ? aCell.textContent.trim() : '';
                let bText = bCell ? bCell.textContent.trim() : '';

                if (column === 'Duration') {
                    // Parse 'MM:SS' to total seconds
                    aText = parseDuration(aText);
                    bText = parseDuration(bText);
                } else if (isNumeric) {
                    aText = parseFloat(aText) || 0;
                    bText = parseFloat(bText) || 0;
                } else {
                    aText = aText.toLowerCase();
                    bText = bText.toLowerCase();
                }

                if (aText < bText) return order === 'asc' ? -1 : 1;
                if (aText > bText) return order === 'asc' ? 1 : -1;
                return 0;
            });

            // Update the table
            const tbody = table.querySelector('tbody');
            tbody.innerHTML = '';
            sortedRows.forEach(function(row) {
                tbody.appendChild(row);
            });

            applyStriping(table);
        });
    });

    // Initial sort by Artist, then Song Title
    sortTableByMultipleColumns(tableRows, table, ['Main Artist', 'Song']);
}

function sortTableByMultipleColumns(tableRows, table, columns) {
    tableRows.sort(function(a, b) {
        for (let i = 0; i < columns.length; i++) {
            const column = columns[i];
            const isNumeric = ['Year Released', 'BPM'].includes(column);
            let aCell = a.querySelector(`td[data-column="${column}"]`);
            let bCell = b.querySelector(`td[data-column="${column}"]`);
            let aText = aCell ? aCell.textContent.trim() : '';
            let bText = bCell ? bCell.textContent.trim() : '';

            if (column === 'Duration') {
                // Parse 'MM:SS' to total seconds
                aText = parseDuration(aText);
                bText = parseDuration(bText);
            } else if (isNumeric) {
                aText = parseFloat(aText) || 0;
                bText = parseFloat(bText) || 0;
            } else {
                aText = aText.toLowerCase();
                bText = bText.toLowerCase();
            }

            if (aText < bText) return -1;
            if (aText > bText) return 1;
            // If equal, continue to next column
        }
        return 0;
    });

    // Update the table
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    tableRows.forEach(function(row) {
        tbody.appendChild(row);
    });

    applyStriping(table);
}

function applyStriping(table) {
    const visibleRows = Array.from(table.querySelectorAll('tbody tr')).filter(row => row.style.display !== 'none');
    visibleRows.forEach((row, index) => {
        row.classList.remove('bg-light', 'bg-white');
        if (index % 2 === 0) {
            row.classList.add('bg-light');
        } else {
            row.classList.add('bg-white');
        }
    });
}

// Function to parse 'MM:SS' to total seconds
function parseDuration(durationStr) {
    const parts = durationStr.split(':');
    if (parts.length === 2) {
        const minutes = parseInt(parts[0], 10);
        const seconds = parseInt(parts[1], 10);
        return minutes * 60 + seconds;
    }
    return 0;
}// Existing search_sort.js content
document.addEventListener('DOMContentLoaded', function() {
    initializeTable('songs-table');
    initializeTable('songs-table-all');
    initializeTable('stats-table');
});

function initializeTable(tableId) {
    const searchBoxId = tableId === 'songs-table' ? 'search-box' : 'search-box-all';
    const searchBox = document.getElementById(searchBoxId);
    const table = document.getElementById(tableId);
    
    if (!table) {
        console.warn(`Table with id '${tableId}' not found.`);
        return;
    }
    
    let tableRows = Array.from(table.querySelectorAll('tbody tr'));
    const headers = table.querySelectorAll(`th.sortable[data-column]`);
    
    // Search functionality
    if (searchBox) {
        searchBox.addEventListener('keyup', function() {
            const searchTerm = searchBox.value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, "").trim();

            tableRows.forEach(function(row) {
                let searchText = row.getAttribute('data-search');
                if (searchText) {
                    searchText = searchText.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, "").trim();
                    if (searchText.indexOf(searchTerm) === -1) {
                        row.style.display = 'none';
                    } else {
                        row.style.display = '';
                    }
                }
            });

            applyStriping(table);
        });
    }
    
    // Sorting functionality
    headers.forEach(function(header) {
        header.addEventListener('click', function() {
            const column = header.getAttribute('data-column');
            let order = header.getAttribute('data-order') || 'asc';
            const isNumeric = ['Year Released', 'BPM'].includes(column);

            // Toggle the sorting order
            order = order === 'asc' ? 'desc' : 'asc';
            header.setAttribute('data-order', order);

            // Remove 'sorted' class from other headers and reset their data-order
            headers.forEach(h => {
                if (h !== header) {
                    h.classList.remove('sorted');
                    h.removeAttribute('data-order');
                }
            });

            // Add 'sorted' class to the active header
            header.classList.add('sorted');

            // Sort rows
            const sortedRows = tableRows.sort(function(a, b) {
                let aCell = a.querySelector(`td[data-column="${column}"]`);
                let bCell = b.querySelector(`td[data-column="${column}"]`);
                let aText = aCell ? aCell.textContent.trim() : '';
                let bText = bCell ? bCell.textContent.trim() : '';

                if (column === 'Duration') {
                    // Parse 'MM:SS' to total seconds
                    aText = parseDuration(aText);
                    bText = parseDuration(bText);
                } else if (isNumeric) {
                    aText = parseFloat(aText) || 0;
                    bText = parseFloat(bText) || 0;
                } else {
                    aText = aText.toLowerCase();
                    bText = bText.toLowerCase();
                }

                if (aText < bText) return order === 'asc' ? -1 : 1;
                if (aText > bText) return order === 'asc' ? 1 : -1;
                return 0;
            });

            // Update the table
            const tbody = table.querySelector('tbody');
            tbody.innerHTML = '';
            sortedRows.forEach(function(row) {
                tbody.appendChild(row);
            });

            applyStriping(table);
        });
    });

    // Initial sort by Artist, then Song Title
    sortTableByMultipleColumns(tableRows, table, ['Main Artist', 'Song']);
}

function sortTableByMultipleColumns(tableRows, table, columns) {
    tableRows.sort(function(a, b) {
        for (let i = 0; i < columns.length; i++) {
            const column = columns[i];
            const isNumeric = ['Year Released', 'BPM'].includes(column);
            let aCell = a.querySelector(`td[data-column="${column}"]`);
            let bCell = b.querySelector(`td[data-column="${column}"]`);
            let aText = aCell ? aCell.textContent.trim() : '';
            let bText = bCell ? bCell.textContent.trim() : '';

            if (column === 'Duration') {
                // Parse 'MM:SS' to total seconds
                aText = parseDuration(aText);
                bText = parseDuration(bText);
            } else if (isNumeric) {
                aText = parseFloat(aText) || 0;
                bText = parseFloat(bText) || 0;
            } else {
                aText = aText.toLowerCase();
                bText = bText.toLowerCase();
            }

            if (aText < bText) return -1;
            if (aText > bText) return 1;
            // If equal, continue to next column
        }
        return 0;
    });

    // Update the table
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    tableRows.forEach(function(row) {
        tbody.appendChild(row);
    });

    applyStriping(table);
}

function applyStriping(table) {
    const visibleRows = Array.from(table.querySelectorAll('tbody tr')).filter(row => row.style.display !== 'none');
    visibleRows.forEach((row, index) => {
        row.classList.remove('bg-light', 'bg-white');
        if (index % 2 === 0) {
            row.classList.add('bg-light');
        } else {
            row.classList.add('bg-white');
        }
    });
}

// Function to parse 'MM:SS' to total seconds
function parseDuration(durationStr) {
    const parts = durationStr.split(':');
    if (parts.length === 2) {
        const minutes = parseInt(parts[0], 10);
        const seconds = parseInt(parts[1], 10);
        return minutes * 60 + seconds;
    }
    return 0;
}