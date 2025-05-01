/**
 * Improved fetch response handler that better extracts error information
 * Usage: 
 * Replace the fetch .then handlers with:
 * 
 * fetch('/url', options)
 *   .then(handleFetchResponse)
 *   .then(data => { ... success handling ... })
 *   .catch(err => { ... improved error handling ... })
 */
function handleFetchResponse(response) {
    return response.text().then(text => {
        // Try to parse the response as JSON
        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            // If not JSON, use the text directly
            data = { message: text };
        }
        
        // If response was not ok, format an error with all available info
        if (!response.ok) {
            const error = new Error(data.message || response.statusText || 'Unknown error');
            error.response = response;
            error.status = response.status;
            error.data = data;
            throw error;
        }
        
        return data;
    });
} 