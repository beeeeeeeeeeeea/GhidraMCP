package com.lauriewired.ghidramcp.core;

import ghidra.program.model.address.Address;

/**
 * A failure that is reported to the client as a structured error with a stable code.
 */
public class McpException extends RuntimeException {

	private final String code;
	private final int status;

	public McpException(String code, int status, String message) {
		super(message);
		this.code = code;
		this.status = status;
	}

	public McpException(String code, int status, String message, Throwable cause) {
		super(message, cause);
		this.code = code;
		this.status = status;
	}

	public String code() {
		return code;
	}

	public int status() {
		return status;
	}

	public static McpException noProgram() {
		return new McpException("NO_PROGRAM", 409, "No program is open");
	}

	public static McpException missingParameter(String name) {
		return new McpException("MISSING_PARAMETER", 400, "Missing required parameter '" + name + "'");
	}

	public static McpException invalidParameter(String message) {
		return new McpException("INVALID_PARAMETER", 400, message);
	}

	public static McpException badAddress(String address) {
		return new McpException("BAD_ADDRESS", 400, "Invalid address: " + address);
	}

	public static McpException functionNotFound(String what) {
		return new McpException("FUNCTION_NOT_FOUND", 404, "No function found " + what);
	}

	public static McpException functionExists(Address address, String name) {
		return new McpException("FUNCTION_EXISTS", 409,
			"A function '" + name + "' already exists at or contains " + address);
	}

	public static McpException notCode(Address address) {
		return new McpException("NOT_CODE", 409,
			"No instruction starts at " + address + "; disassemble the bytes first");
	}

	public static McpException dataExists(Address address) {
		return new McpException("DATA_EXISTS", 409,
			"Data is already defined at or contains " + address +
				"; pass overwrite=true to replace it");
	}

	public static McpException notFound(String message) {
		return new McpException("NOT_FOUND", 404, message);
	}

	public static McpException ambiguous(String message) {
		return new McpException("AMBIGUOUS_NAME", 409, message);
	}

	public static McpException conflict(String message) {
		return new McpException("NAME_CONFLICT", 409, message);
	}

	public static McpException unsupported(String message) {
		return new McpException("UNSUPPORTED", 501, message);
	}

	public static McpException readOnly(String message) {
		return new McpException("READ_ONLY", 409, message);
	}

	public static McpException decompileFailed(String message) {
		return new McpException("DECOMPILE_FAILED", 500, message);
	}

	public static McpException failed(String message, Throwable cause) {
		return new McpException("OPERATION_FAILED", 500, message, cause);
	}

	public static McpException failed(String message) {
		return new McpException("OPERATION_FAILED", 500, message);
	}
}
