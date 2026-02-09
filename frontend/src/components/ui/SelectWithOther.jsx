import React, { useState, useEffect, useRef } from "react";
import { safeDisplay } from "../../utils/format";
import Input from "./Input";

export default function SelectWithOther({
  options = [],
  value,
  onChange,
  className = "",
  placeholder = "Select or type...",
}) {
  const [inputValue, setInputValue] = useState(value || "");
  const [showDropdown, setShowDropdown] = useState(false);
  const [filteredOptions, setFilteredOptions] = useState(options);
  const inputRef = useRef(null);

  useEffect(() => {
    setInputValue(value || "");
  }, [value]);

  useEffect(() => {
    if (inputValue.trim() === "") {
      setFilteredOptions(options);
    } else {
      setFilteredOptions(
        options.filter(
          (o) =>
            o.label.toLowerCase().includes(inputValue.toLowerCase()) ||
            o.value.toLowerCase().includes(inputValue.toLowerCase())
        )
      );
    }
  }, [inputValue, options]);

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    setShowDropdown(true);
  };

  const handleInputBlur = () => {
    if (inputValue !== value) onChange(inputValue);
    setTimeout(() => setShowDropdown(false), 200);
  };

  const handleOptionClick = (optionValue) => {
    setInputValue(optionValue);
    setShowDropdown(false);
    onChange(optionValue);
    if (inputRef.current) inputRef.current.blur();
  };

  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      setShowDropdown(false);
      if (inputRef.current) inputRef.current.blur();
    }
  };

  return (
    <div className="relative">
      <input
        ref={inputRef}
        value={inputValue}
        onChange={handleInputChange}
        onFocus={() => setShowDropdown(true)}
        onBlur={handleInputBlur}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoComplete="off"
        className={`w-full rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 ${className}`}
      />
      {showDropdown && filteredOptions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-xl shadow-lg max-h-60 overflow-auto">
          {filteredOptions.map((o) => (
            <div
              key={o.value}
              onClick={() => handleOptionClick(o.value)}
              className="px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-sm"
            >
              {safeDisplay(o.label)}
            </div>
          ))}
          {inputValue.trim() !== "" &&
            !options.find((o) => o.value === inputValue) && (
              <div
                onClick={() => handleOptionClick(inputValue)}
                className="px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-sm border-t border-gray-300 dark:border-gray-700 text-slate-700 dark:text-slate-300"
              >
                Use "{inputValue}" (custom)
              </div>
            )}
        </div>
      )}
    </div>
  );
}
