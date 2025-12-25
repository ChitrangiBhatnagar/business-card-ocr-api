"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";

// Configure your deployed API URL
const OCR_API_URL = process.env.NEXT_PUBLIC_OCR_API_URL || "https://business-card-ocr-api.onrender.com";

export default function BusinessCardScanner() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);

  const processCard = async (file) => {
    const formData = new FormData();
    formData.append("image", file);

    const response = await fetch(`${OCR_API_URL}/api/process`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    setIsProcessing(true);
    setError(null);

    try {
      const newResults = [];

      for (const file of acceptedFiles) {
        try {
          const result = await processCard(file);
          newResults.push(result);
        } catch (err) {
          newResults.push({
            success: false,
            error: err.message || "Processing failed",
          });
        }
      }

      setResults((prev) => [...prev, ...newResults]);
    } catch (err) {
      setError(err.message || "An error occurred");
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"],
    },
    multiple: true,
  });

  const addToContacts = async (contact) => {
    // TODO: Integrate with your CRM/contact system
    console.log("Adding to contacts:", contact);
    alert(`Added ${contact.name || contact.email} to contacts!`);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6 text-white">
        📇 Business Card Scanner
      </h2>

      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all
          ${isDragActive 
            ? "border-blue-500 bg-blue-500/10" 
            : "border-gray-600 hover:border-blue-400 hover:bg-gray-800/50"
          }`}
      >
        <input {...getInputProps()} />
        {isProcessing ? (
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent" />
            <p className="text-gray-400">Processing business cards...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div className="text-5xl">📸</div>
            <p className="text-gray-300">
              {isDragActive
                ? "Drop business cards here..."
                : "Drag & drop business cards or click to upload"}
            </p>
            <p className="text-gray-500 text-sm">
              Supports PNG, JPG, WEBP • Multiple cards supported
            </p>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-500/20 border border-red-500 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="mt-8">
          <h3 className="text-xl font-semibold mb-4 text-white">
            Extracted Contacts ({results.filter((r) => r.success).length})
          </h3>

          <div className="space-y-4">
            {results.map((result, index) => (
              <div
                key={index}
                className="bg-gray-800 rounded-xl p-6 border border-gray-700"
              >
                {result.success && result.contact_data ? (
                  <div className="flex gap-6">
                    {/* Company Logo */}
                    {(result.contact_data.company_logo ||
                      result.company_enrichment?.logo_url) && (
                      <div className="flex-shrink-0">
                        <img
                          src={
                            result.contact_data.company_logo ||
                            result.company_enrichment?.logo_url
                          }
                          alt="Company logo"
                          className="w-16 h-16 rounded-lg bg-white p-2 object-contain"
                          onError={(e) => (e.currentTarget.style.display = "none")}
                        />
                      </div>
                    )}

                    {/* Contact Info */}
                    <div className="flex-1 grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-lg font-semibold text-white">
                          {result.contact_data.name || "Unknown"}
                        </p>
                        <p className="text-gray-400">
                          {result.contact_data.title}
                        </p>
                        <p className="text-blue-400">
                          {result.contact_data.company}
                        </p>
                        {result.contact_data.industry && (
                          <span className="inline-block mt-1 px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded">
                            {result.contact_data.industry}
                          </span>
                        )}
                      </div>

                      <div className="space-y-1">
                        {result.contact_data.email && (
                          <p className="text-gray-300">
                            📧 {result.contact_data.email}
                            {result.field_confidence?.email && (
                              <span
                                className={`ml-2 text-xs px-1.5 py-0.5 rounded ${
                                  result.field_confidence.email >= 0.8
                                    ? "bg-green-500/20 text-green-400"
                                    : result.field_confidence.email >= 0.5
                                    ? "bg-yellow-500/20 text-yellow-400"
                                    : "bg-red-500/20 text-red-400"
                                }`}
                              >
                                {Math.round(result.field_confidence.email * 100)}%
                              </span>
                            )}
                          </p>
                        )}
                        {result.contact_data.phone?.length > 0 && (
                          <p className="text-gray-300">
                            📱 {result.contact_data.phone.join(", ")}
                          </p>
                        )}
                        {result.contact_data.website && (
                          <p className="text-gray-300">
                            🌐 {result.contact_data.website}
                          </p>
                        )}
                        {(result.contact_data.linkedin ||
                          result.company_enrichment?.linkedin_url) && (
                          <a
                            href={
                              result.contact_data.linkedin ||
                              result.company_enrichment?.linkedin_url
                            }
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:underline"
                          >
                            🔗 LinkedIn
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Confidence & Actions */}
                    <div className="flex flex-col items-end gap-2">
                      <div
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          (result.contact_data.confidence_score || 0) >= 0.8
                            ? "bg-green-500/20 text-green-400"
                            : (result.contact_data.confidence_score || 0) >= 0.5
                            ? "bg-yellow-500/20 text-yellow-400"
                            : "bg-red-500/20 text-red-400"
                        }`}
                      >
                        {Math.round(
                          (result.contact_data.confidence_score || 0) * 100
                        )}
                        % confidence
                      </div>

                      <p className="text-xs text-gray-500">
                        {result.ocr_method === "gemini_fallback"
                          ? "🤖 AI Enhanced"
                          : "⚡ Fast OCR"}
                      </p>

                      {result.processing_time_ms && (
                        <p className="text-xs text-gray-600">
                          {result.processing_time_ms}ms
                        </p>
                      )}

                      <button
                        onClick={() => addToContacts(result.contact_data)}
                        className="mt-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm transition-colors"
                      >
                        Add to CRM
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-red-400">
                    ❌ Failed: {result.error || "Unknown error"}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Bulk Actions */}
          <div className="mt-6 flex gap-4">
            <button
              onClick={() => {
                const contacts = results
                  .filter((r) => r.success)
                  .map((r) => r.contact_data);
                console.log("Exporting contacts:", contacts);
                // TODO: Export to your CRM
              }}
              className="px-6 py-3 bg-green-600 hover:bg-green-500 text-white rounded-lg transition-colors"
            >
              Export All to CRM
            </button>

            <button
              onClick={() => setResults([])}
              className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Clear Results
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
