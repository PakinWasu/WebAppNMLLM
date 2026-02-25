import React, { useState, useMemo, useRef, useEffect } from "react";
import { safeDisplay } from "../../utils/format";
import { ChevronDown, Filter, X, Search } from "lucide-react";

// Sort icon component
const SortIcon = ({ direction }) => (
  <span className="ml-1 inline-flex flex-col text-[8px] leading-none opacity-60">
    <span className={direction === 'asc' ? 'text-sky-400' : ''}>▲</span>
    <span className={direction === 'desc' ? 'text-sky-400' : ''}>▼</span>
  </span>
);

// Header filter dropdown component (modern style)
const HeaderFilterDropdown = ({ column, data, filterValue, onFilterChange, onClose, position = "left" }) => {
  const dropdownRef = useRef(null);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Get unique values for this column
  const uniqueValues = useMemo(() => {
    const values = new Set();
    data.forEach(row => {
      let val;
      if (column.cell) {
        const rendered = column.cell(row, 0);
        if (typeof rendered === 'string') {
          val = rendered;
        } else if (React.isValidElement(rendered)) {
          const extractText = (el) => {
            if (typeof el === 'string') return el;
            if (typeof el === 'number') return String(el);
            if (Array.isArray(el)) return el.map(extractText).join('');
            if (el?.props?.children) return extractText(el.props.children);
            return '';
          };
          val = extractText(rendered);
        } else if (val != null) {
          val = String(rendered);
        }
      } else {
        val = row[column.key];
      }
      if (val != null && val !== "" && val !== "—") {
        values.add(String(val));
      }
    });
    return Array.from(values).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  }, [data, column]);

  const filteredValues = useMemo(() => {
    if (!searchTerm) return uniqueValues;
    const term = searchTerm.toLowerCase();
    return uniqueValues.filter(v => v.toLowerCase().includes(term));
  }, [uniqueValues, searchTerm]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  const positionClass = position === "right" ? "right-0" : "left-0";

  return (
    <div 
      ref={dropdownRef}
      className={`absolute top-full ${positionClass} mt-1 z-50 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl min-w-[200px] max-w-[280px]`}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Search input */}
      <div className="p-2 border-b border-slate-700">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-7 pr-2 py-1.5 text-xs rounded bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500"
            autoFocus
          />
        </div>
      </div>
      
      {/* Options list */}
      <div className="max-h-[200px] overflow-y-auto">
        <button
          onClick={() => { onFilterChange(null); onClose(); }}
          className={`w-full px-3 py-2 text-left text-xs hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition-colors ${
            !filterValue 
              ? 'text-sky-700 bg-sky-100 dark:text-sky-400 dark:bg-sky-800/50' 
              : 'text-slate-700 dark:text-slate-300'
          }`}
        >
          <span className="w-4 flex justify-center">{!filterValue && "✓"}</span>
          <span>All</span>
        </button>
        {filteredValues.map((val, i) => (
          <button
            key={i}
            onClick={() => { onFilterChange(val); onClose(); }}
            className={`w-full px-3 py-2 text-left text-xs hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 truncate transition-colors ${
              filterValue === val 
                ? 'text-sky-700 bg-sky-100 dark:text-sky-400 dark:bg-sky-800/50' 
                : 'text-slate-700 dark:text-slate-300'
            }`}
          >
            <span className="w-4 flex justify-center">{filterValue === val && "✓"}</span>
            <span className="truncate">{val}</span>
          </button>
        ))}
        {filteredValues.length === 0 && (
          <div className="px-3 py-3 text-xs text-slate-500 dark:text-slate-400 text-center">No matches</div>
        )}
      </div>
    </div>
  );
};

// Global filter dropdown (for top bar)
const GlobalFilterDropdown = ({ 
  label, 
  column, 
  data, 
  filterValue, 
  onFilterChange,
  columns
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const [searchTerm, setSearchTerm] = useState("");

  const col = columns.find(c => c.key === column);
  
  const uniqueValues = useMemo(() => {
    if (!col) return [];
    const values = new Set();
    data.forEach(row => {
      let val;
      if (col.cell) {
        const rendered = col.cell(row, 0);
        if (typeof rendered === 'string') {
          val = rendered;
        } else if (React.isValidElement(rendered)) {
          const extractText = (el) => {
            if (typeof el === 'string') return el;
            if (typeof el === 'number') return String(el);
            if (Array.isArray(el)) return el.map(extractText).join('');
            if (el?.props?.children) return extractText(el.props.children);
            return '';
          };
          val = extractText(rendered);
        } else if (val != null) {
          val = String(rendered);
        }
      } else {
        val = row[column];
      }
      if (val != null && val !== "" && val !== "—") {
        values.add(String(val));
      }
    });
    return Array.from(values).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  }, [data, col, column]);

  const filteredValues = useMemo(() => {
    if (!searchTerm) return uniqueValues;
    const term = searchTerm.toLowerCase();
    return uniqueValues.filter(v => v.toLowerCase().includes(term));
  }, [uniqueValues, searchTerm]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
        setSearchTerm("");
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const displayValue = filterValue || `All (${label})`;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 px-3 py-2 text-xs rounded-lg border transition-colors min-w-[140px] justify-between ${
          filterValue 
            ? 'bg-sky-100 border-sky-300 text-sky-700 dark:bg-sky-900/30 dark:border-sky-600 dark:text-sky-400' 
            : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50 hover:border-slate-400 dark:bg-slate-800 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:border-slate-500'
        }`}
      >
        <span className="truncate max-w-[150px]">{displayValue}</span>
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 z-50 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl min-w-[200px] max-w-[280px]">
          <div className="p-2 border-b border-slate-700">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-7 pr-2 py-1.5 text-xs rounded bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500"
                autoFocus
              />
            </div>
          </div>
          <div className="max-h-[200px] overflow-y-auto">
            <button
              onClick={() => { onFilterChange(null); setIsOpen(false); setSearchTerm(""); }}
              className={`w-full px-3 py-2 text-left text-xs hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition-colors ${
                !filterValue 
                  ? 'text-sky-700 bg-sky-100 dark:text-sky-400 dark:bg-sky-800/50' 
                  : 'text-slate-700 dark:text-slate-300'
              }`}
            >
              <span className="w-4 flex justify-center">{!filterValue && "✓"}</span>
              <span>All ({label})</span>
            </button>
            {filteredValues.map((val, i) => (
              <button
                key={i}
                onClick={() => { onFilterChange(val); setIsOpen(false); setSearchTerm(""); }}
                className={`w-full px-3 py-2 text-left text-xs hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 truncate transition-colors ${
                  filterValue === val 
                    ? 'text-sky-700 bg-sky-100 dark:text-sky-400 dark:bg-sky-800/50' 
                    : 'text-slate-700 dark:text-slate-300'
                }`}
              >
                <span className="w-4 flex justify-center">{filterValue === val && "✓"}</span>
                <span className="truncate">{val}</span>
              </button>
            ))}
            {filteredValues.length === 0 && (
              <div className="px-3 py-3 text-xs text-slate-500 dark:text-slate-400 text-center">No matches</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default function Table({
  columns,
  data,
  empty = "No data",
  containerClassName = "",
  minWidthClass = "min-w-full",
  onRowClick,
  selectedIndex,
  filterable = true,
  sortable = true,
  // New props for enhanced filtering
  searchable = false,
  searchPlaceholder = "Search...",
  searchValue = "",
  onSearchChange,
  globalFilters = [], // Array of { key: string, label: string } for top filter dropdowns
  title = null, // Optional table title
  actions = null, // Optional actions (buttons etc.) for header
  showToolbar = null, // Force show/hide toolbar. If null, auto-detect based on searchable/globalFilters/title
}) {
  const [filters, setFilters] = useState({});
  const [sortConfig, setSortConfig] = useState({ key: null, direction: null });
  const [openFilter, setOpenFilter] = useState(null);
  const [internalSearch, setInternalSearch] = useState("");

  // Use external or internal search
  const searchTerm = onSearchChange ? searchValue : internalSearch;
  const handleSearchChange = onSearchChange || setInternalSearch;

  const textSizeClass = containerClassName.includes("text-[")
    ? containerClassName.match(/text-\[[^\]]+\]/)?.[0]
    : null;
  const tableTextSize = textSizeClass || "text-xs";
  const headerTextSize = textSizeClass
    ? textSizeClass.replace("text-", "text-").replace("px]", "px]")
    : "text-[10px]";
  const headerAtLeastXs = headerTextSize === "text-[10px]" ? "text-xs" : headerTextSize;

  // Determine if we should show the toolbar
  const shouldShowToolbar = showToolbar !== null 
    ? showToolbar 
    : (searchable || globalFilters.length > 0 || title);

  // Filter and sort data
  const processedData = useMemo(() => {
    let result = [...data];

    // Apply global search filter
    if (searchTerm.trim()) {
      const term = searchTerm.trim().toLowerCase();
      result = result.filter(row => {
        // Search across all columns
        return columns.some(col => {
          let cellVal;
          if (col.cell) {
            const rendered = col.cell(row, 0);
            if (typeof rendered === 'string') {
              cellVal = rendered;
            } else if (React.isValidElement(rendered)) {
              const extractText = (el) => {
                if (typeof el === 'string') return el;
                if (typeof el === 'number') return String(el);
                if (Array.isArray(el)) return el.map(extractText).join('');
                if (el?.props?.children) return extractText(el.props.children);
                return '';
              };
              cellVal = extractText(rendered);
            } else {
              cellVal = String(rendered ?? '');
            }
          } else {
            cellVal = String(row[col.key] ?? '');
          }
          return cellVal.toLowerCase().includes(term);
        });
      });
    }

    // Apply column filters
    Object.entries(filters).forEach(([key, value]) => {
      if (value != null && value !== "") {
        const col = columns.find(c => c.key === key);
        result = result.filter(row => {
          let cellVal;
          if (col?.cell) {
            const rendered = col.cell(row, 0);
            if (typeof rendered === 'string') {
              cellVal = rendered;
            } else if (React.isValidElement(rendered)) {
              const extractText = (el) => {
                if (typeof el === 'string') return el;
                if (typeof el === 'number') return String(el);
                if (Array.isArray(el)) return el.map(extractText).join('');
                if (el?.props?.children) return extractText(el.props.children);
                return '';
              };
              cellVal = extractText(rendered);
            } else {
              cellVal = String(rendered ?? '');
            }
          } else {
            cellVal = String(row[key] ?? '');
          }
          return cellVal === value;
        });
      }
    });

    // Apply sorting
    if (sortConfig.key && sortConfig.direction) {
      const col = columns.find(c => c.key === sortConfig.key);
      result.sort((a, b) => {
        let aVal, bVal;
        if (col?.cell) {
          const extractVal = (row) => {
            const rendered = col.cell(row, 0);
            if (typeof rendered === 'string') return rendered;
            if (typeof rendered === 'number') return rendered;
            if (React.isValidElement(rendered)) {
              const extractText = (el) => {
                if (typeof el === 'string') return el;
                if (typeof el === 'number') return el;
                if (Array.isArray(el)) return el.map(extractText).join('');
                if (el?.props?.children) return extractText(el.props.children);
                return '';
              };
              return extractText(rendered);
            }
            return String(rendered ?? '');
          };
          aVal = extractVal(a);
          bVal = extractVal(b);
        } else {
          aVal = a[sortConfig.key];
          bVal = b[sortConfig.key];
        }
        
        // Handle nulls
        if (aVal == null || aVal === "—") aVal = "";
        if (bVal == null || bVal === "—") bVal = "";
        
        // Numeric comparison if both are numbers
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);
        if (!isNaN(aNum) && !isNaN(bNum)) {
          return sortConfig.direction === 'asc' ? aNum - bNum : bNum - aNum;
        }
        
        // String comparison
        const aStr = String(aVal).toLowerCase();
        const bStr = String(bVal).toLowerCase();
        if (sortConfig.direction === 'asc') {
          return aStr.localeCompare(bStr, undefined, { numeric: true });
        }
        return bStr.localeCompare(aStr, undefined, { numeric: true });
      });
    }

    return result;
  }, [data, filters, sortConfig, columns, searchTerm]);

  const handleSort = (key) => {
    if (!sortable) return;
    setSortConfig(prev => {
      if (prev.key !== key) return { key, direction: 'asc' };
      if (prev.direction === 'asc') return { key, direction: 'desc' };
      if (prev.direction === 'desc') return { key: null, direction: null };
      return { key, direction: 'asc' };
    });
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => {
      const next = { ...prev };
      if (value == null) {
        delete next[key];
      } else {
        next[key] = value;
      }
      return next;
    });
  };

  const activeFiltersCount = Object.keys(filters).length + (searchTerm.trim() ? 1 : 0);

  const clearAllFilters = () => {
    setFilters({});
    setSortConfig({ key: null, direction: null });
    handleSearchChange("");
  };

  return (
    <div className={`overflow-hidden w-full flex flex-col ${containerClassName}`}>
      {/* Toolbar - Search only (title and global filters removed) */}
      {shouldShowToolbar && (
        <div className="flex flex-wrap items-center gap-3 px-3 py-2.5 bg-slate-50 border-b border-slate-200 dark:bg-slate-800/50 dark:border-slate-700">
          {/* Search Box - takes full width */}
          {searchable && (
            <div className="relative flex-1 min-w-[200px] max-w-[400px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder={searchPlaceholder}
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-white dark:bg-slate-900/80 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500"
              />
              {searchTerm && (
                <button
                  onClick={() => handleSearchChange("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-slate-500 hover:text-slate-300"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}

          {/* Actions */}
          {actions && (
            <div className="ml-auto flex items-center gap-2">
              {actions}
            </div>
          )}
        </div>
      )}

      {/* Active filters bar */}
      {activeFiltersCount > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 bg-sky-50 border-b border-sky-200 dark:bg-sky-900/20 dark:border-sky-800/50">
          <span className="text-xs text-sky-700 dark:text-sky-400 font-medium">Active Filters:</span>
          <div className="flex flex-wrap gap-1.5">
            {searchTerm.trim() && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-sky-100 text-sky-700 dark:bg-sky-800/50 dark:text-sky-300 rounded-full">
                <span className="font-medium">Search:</span>
                <span className="max-w-[100px] truncate">{searchTerm}</span>
                <button 
                  onClick={() => handleSearchChange("")}
                  className="ml-0.5 hover:text-sky-100"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {Object.entries(filters).map(([key, value]) => {
              const col = columns.find(c => c.key === key);
              return (
                <span 
                  key={key} 
                  className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-sky-800/50 text-sky-300 rounded-full"
                >
                  <span className="font-medium">{col?.header || key}:</span>
                  <span className="max-w-[100px] truncate">{value}</span>
                  <button 
                    onClick={() => handleFilterChange(key, null)}
                    className="ml-0.5 hover:text-sky-100"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              );
            })}
          </div>
          <button 
            onClick={clearAllFilters}
            className="ml-auto text-xs text-sky-400 hover:text-sky-200 font-medium"
          >
            Clear all
          </button>
        </div>
      )}
      
      {/* Table */}
      <div className="overflow-auto flex-1">
        <table
          className={`${minWidthClass} w-full divide-y divide-slate-200 dark:divide-slate-700`}
          style={{ tableLayout: "auto", width: "100%" }}
        >
          <thead className="bg-slate-100 dark:bg-slate-800 sticky top-0 z-10">
            <tr>
              {columns.map((c, colIndex) => {
                const isFilterable = filterable && c.key && c.filterable !== false;
                const isSortable = sortable && c.key && c.sortable !== false;
                const hasFilter = filters[c.key] != null;
                const sortDirection = sortConfig.key === c.key ? sortConfig.direction : null;
                const isLastColumn = colIndex === columns.length - 1;
                
                return (
                  <th
                    key={c.key || c.header}
                    title={c.title || undefined}
                    className={`px-3 py-2.5 text-left ${headerAtLeastXs} font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700 whitespace-nowrap relative group`}
                    style={c.width ? { minWidth: c.width } : undefined}
                  >
                    <div className="flex items-center gap-1.5">
                      {/* Header text - clickable for sort */}
                      <button
                        onClick={() => isSortable && handleSort(c.key)}
                        className={`flex items-center gap-0.5 ${isSortable ? 'hover:text-slate-900 dark:hover:text-slate-200 cursor-pointer' : ''} transition-colors`}
                        disabled={!isSortable}
                      >
                        {safeDisplay(c.header)}
                        {isSortable && <SortIcon direction={sortDirection} />}
                      </button>
                      
                      {/* Filter dropdown trigger - modern style */}
                      {isFilterable && (
                        <button
                          onClick={(e) => { e.stopPropagation(); setOpenFilter(openFilter === c.key ? null : c.key); }}
                          className={`p-1 rounded transition-all ${
                            hasFilter 
                              ? 'text-sky-700 bg-sky-100 dark:text-sky-400 dark:bg-sky-900/30' 
                              : 'text-slate-500 opacity-0 group-hover:opacity-100 hover:text-slate-700 hover:bg-slate-200 dark:hover:text-slate-300 dark:hover:bg-slate-700'
                          }`}
                          title="Filter"
                        >
                          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${openFilter === c.key ? 'rotate-180' : ''}`} />
                        </button>
                      )}
                    </div>
                    
                    {/* Filter dropdown */}
                    {openFilter === c.key && isFilterable && (
                      <HeaderFilterDropdown
                        column={c}
                        data={data}
                        filterValue={filters[c.key]}
                        onFilterChange={(val) => handleFilterChange(c.key, val)}
                        onClose={() => setOpenFilter(null)}
                        position={isLastColumn ? "right" : "left"}
                      />
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-100 dark:bg-slate-900 dark:divide-slate-800">
            {processedData.length === 0 && (
              <tr>
                <td
                  className={`px-4 py-8 ${tableTextSize} text-center text-slate-500`}
                  colSpan={columns.length}
                >
                  {safeDisplay(empty)}
                </td>
              </tr>
            )}
            {processedData.map((row, i) => (
              <tr
                key={i}
                role={onRowClick ? "button" : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                onClick={onRowClick ? () => onRowClick(row, i) : undefined}
                onKeyDown={onRowClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onRowClick(row, i); } } : undefined}
                className={`transition-colors ${onRowClick ? "cursor-pointer" : ""} ${
                  selectedIndex === i 
                    ? "bg-sky-50 dark:bg-sky-900/30 ring-inset ring-1 ring-sky-500 dark:ring-sky-600" 
                    : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
                }`}
              >
                {columns.map((c) => {
                  let cellContent;
                  if (c.cell) {
                    const raw = c.cell(row, i);
                    if (
                      typeof raw === "object" &&
                      raw !== null &&
                      !React.isValidElement(raw)
                    ) {
                      cellContent = Array.isArray(raw)
                        ? raw.join(", ")
                        : JSON.stringify(raw);
                    } else {
                      cellContent = raw;
                    }
                  } else {
                    const raw = row[c.key];
                    if (raw === null || raw === undefined) {
                      cellContent = "—";
                    } else if (typeof raw === "object" && raw !== null) {
                      if (Array.isArray(raw)) {
                        cellContent = raw.length ? raw.join(", ") : "—";
                      } else if (
                        Object.prototype.hasOwnProperty.call(raw, "total") &&
                        Object.prototype.hasOwnProperty.call(raw, "up")
                      ) {
                        cellContent = `${raw.total ?? 0}/${raw.up ?? 0}/${raw.down ?? 0}/${raw.adminDown ?? 0}`;
                      } else {
                        cellContent = JSON.stringify(raw);
                      }
                    } else {
                      cellContent = raw;
                    }
                  }
                  return (
                    <td
                      key={c.key || c.header}
                      className={`px-3 py-2 ${tableTextSize} text-slate-700 dark:text-slate-200 whitespace-nowrap`}
                      style={c.width ? { minWidth: c.width } : undefined}
                    >
                      {cellContent}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Footer with row count */}
      {data.length > 0 && (
        <div className="px-3 py-2 bg-slate-50 border-t border-slate-200 text-xs text-slate-600 dark:bg-slate-800/50 dark:border-slate-700 dark:text-slate-500">
          {processedData.length === data.length 
            ? `${data.length} row${data.length !== 1 ? 's' : ''}`
            : `Showing ${processedData.length} of ${data.length} row${data.length !== 1 ? 's' : ''}`
          }
        </div>
      )}
    </div>
  );
}
